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
import logging

logger = logging.getLogger(__name__)

# Default conversion margin (e.g., 0.5%)
CONVERSION_MARGIN = getattr(settings, 'CONVERSION_MARGIN', Decimal('0.005'))

class RateQueryAPIView(APIView):
    """GET /api/v1/rates/latest/?base=USD&target=NGN"""
    def get(self, request):
        serializer = RateQuerySerializer(data=request.query_params)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return Response(
                {"error": e.detail if isinstance(e.detail, dict) else str(e.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        base_currency = serializer.validated_data["base"].upper()
        counter_currency = serializer.validated_data["target"].upper()
        try:
            rate_value = ExchangeRate.objects.get_latest_rate(
                base_currency=base_currency,
                counter_currency=counter_currency,
            )
            if rate_value is None:
                logger.warning(f"No rate found for {base_currency}/{counter_currency}")
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
            logger.info(f"Rate retrieved: {base_currency}/{counter_currency} = {rate_value}")
            return Response(
                LatestRateSerializer(response_data).data,
                status=status.HTTP_200_OK,
            )
        except ExchangeRate.DoesNotExist:
            logger.warning(f"DoesNotExist for {base_currency}/{counter_currency}")
            return Response(
                {"error": f"No valid exchange rate found for {base_currency}/{counter_currency}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error during rate query: {e}")
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
            logger.error(f"Validation error: {e}")
            return Response(
                {"error": e.detail if isinstance(e.detail, dict) else str(e.detail)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        input_amount = Decimal(str(data["amount"]))
        base_currency = data["base"].upper()
        target_currency = data["target"].upper()
        try:
            logger.info(f"Starting conversion: {input_amount} {base_currency} to {target_currency}")
            # Use get_latest_rate to fetch the rate, consistent with RateQueryAPIView
            rate_value = ExchangeRate.objects.get_latest_rate(
                base_currency=base_currency,
                counter_currency=target_currency,
            )
            logger.debug(f"Rate value: {rate_value}")
            # Apply conversion margin
            margin = getattr(settings, 'CONVERSION_MARGIN', Decimal('0.005'))
            spread_factor = Decimal("1.0") - margin
            adjusted_rate = (rate_value * spread_factor).quantize(Decimal("0.0001"))
            output_amount = (input_amount * adjusted_rate).quantize(Decimal("0.01"))
            logger.debug(f"Adjusted rate: {adjusted_rate}, Output amount: {output_amount}")

            # Audit conversion in transaction
            with transaction.atomic():
                # Fetch the ExchangeRate record to link in the audit
                direct_rate = ExchangeRate.objects.filter(
                    base_currency='EUR',
                    counter_currency=base_currency,
                ).order_by('-fetched_at').first()
                if not direct_rate:
                    raise ExchangeRate.DoesNotExist(f"No rate found for EUR/{base_currency}")
                eur_to_target = ExchangeRate.objects.filter(
                    base_currency='EUR',
                    counter_currency=target_currency,
                ).order_by('-fetched_at').first()
                if not eur_to_target:
                    raise ExchangeRate.DoesNotExist(f"No rate found for EUR/{target_currency}")
                rate_record = eur_to_target  # Use EUR→target as the reference rate for audit

                audit = ConversionAudit.objects.create(
                    rate_used=rate_record,
                    input_amount=input_amount,
                    output_amount=output_amount,
                    margin_applied=margin,
                    converted_at=timezone.now(),
                )
            logger.info(f"Conversion successful: {input_amount} {base_currency} = {output_amount} {target_currency}")
            # Serialize the audit instance
            serializer = ConversionResponseSerializer(audit)
            response_data = serializer.data
            # Add effective_rate to the response data
            response_data['effective_rate'] = float(adjusted_rate)
            return Response(response_data, status=status.HTTP_200_OK)

        except InvalidOperation as e:
            logger.error(f"Invalid numerical operation during conversion: {e}")
            return Response(
                {"error": "Invalid numerical operation during conversion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ExchangeRate.DoesNotExist:
            logger.warning(f"DoesNotExist for {base_currency}/{target_currency}")
            return Response(
                {"error": f"No valid exchange rate found for {base_currency}/{target_currency}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Critical error during conversion: {e}", exc_info=True)
            return Response(
                {"error": "Internal error during conversion."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )