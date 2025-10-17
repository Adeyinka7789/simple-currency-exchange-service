from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from exchange_app.models import ExchangeRate, ConversionAudit
from exchange_app.serializers import (
    RateQuerySerializer,
    ConversionRequestSerializer,
    LatestRateSerializer,
    ConversionResponseSerializer,
)

# Default conversion margin (e.g., 0.5%)
CONVERSION_MARGIN = getattr(settings, 'CONVERSION_MARGIN', Decimal('0.005'))


class RateQueryAPIView(APIView):
    """GET /api/v1/rates/latest/?base=USD&target=NGN"""

    def get(self, request):
        serializer = RateQuerySerializer(data=request.query_params)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {"error": e.detail if isinstance(e.detail, dict) else str(e.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_currency = serializer.validated_data["base"].upper()
        counter_currency = serializer.validated_data["target"].upper()

        try:
            # Ensure get_latest_rate() returns a Decimal, not a model
            rate_value = ExchangeRate.objects.get_latest_rate(
                base_currency=base_currency,
                counter_currency=counter_currency,
            )

            if rate_value is None:
                return Response(
                    {"error": f"No valid exchange rate found for {base_currency}/{counter_currency}."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_data = {
                "base_currency": base_currency,
                "counter_currency": counter_currency,
                "rate": rate_value,
                "margin": CONVERSION_MARGIN,
                "fetched_at": timezone.now(),
            }

            return Response(
                LatestRateSerializer(response_data).data,
                status=status.HTTP_200_OK,
            )

        except ExchangeRate.DoesNotExist:
            return Response(
                {"error": f"No valid exchange rate found for {base_currency}/{counter_currency}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            print(f"Error during rate query: {e}")
            return Response(
                {"error": "Internal service error during rate retrieval."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConversionAPIView(APIView):
    """POST /api/v1/conversions/"""

    def post(self, request):
        serializer = ConversionRequestSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {"error": e.detail if isinstance(e.detail, dict) else str(e.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        input_amount = data["amount"]
        from_currency = data["base"].upper()
        to_currency = data["target"].upper()

        try:
            # Get latest rate for conversion
            latest_rate_record = (
                ExchangeRate.objects.filter(
                    base_currency=from_currency,
                    counter_currency=to_currency
                )
                .order_by("-fetched_at")
                .first()
            )

            if not latest_rate_record:
                return Response(
                    {"error": f"No current rate available for {from_currency}/{to_currency}."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Apply conversion margin
            rate_value = latest_rate_record.rate_value
            spread_factor = Decimal("1.0") - CONVERSION_MARGIN
            adjusted_rate = (rate_value * spread_factor).quantize(Decimal("0.0001"))
            output_amount = (input_amount * adjusted_rate).quantize(Decimal("0.01"))

            # Audit conversion in transaction
            with transaction.atomic():
                audit = ConversionAudit.objects.create(
                    rate_used=latest_rate_record,
                    input_amount=input_amount,
                    output_amount=output_amount,
                    margin_applied=CONVERSION_MARGIN,
                )

            return Response(
                ConversionResponseSerializer(audit).data,
                status=status.HTTP_200_OK,
            )

        except InvalidOperation:
            return Response(
                {"error": "Invalid numerical operation during conversion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            print(f"Critical error during conversion: {e}")
            return Response(
                {"error": "Internal error during conversion."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )