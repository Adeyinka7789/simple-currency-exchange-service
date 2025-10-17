from rest_framework import serializers
from decimal import Decimal
from django.conf import settings
from exchange_app.models import ConversionAudit


# ----------------------------
# FR1.2 – Rate Query Input (FIXED: Renamed fields to 'base' and 'target')
# ----------------------------

class RateQuerySerializer(serializers.Serializer):
    """
    Validates the query parameters for a rate lookup.
    """
    base = serializers.CharField(  # FIX: Renamed from 'from_currency'
        max_length=3,
        required=True,
        help_text="Base currency code (e.g., USD)."
    )
    target = serializers.CharField(  # FIX: Renamed from 'to_currency'
        max_length=3,
        required=True,
        help_text="Target currency code (e.g., NGN)."
    )

    def validate(self, data):
        """Ensure currency codes are uppercase and not identical."""
        # FIX: Changed key access from 'from_currency'/'to_currency' to 'base'/'target'
        base = data.get('base', '').upper()
        target = data.get('target', '').upper()

        if not base or not target:
            raise serializers.ValidationError("Both currency codes are required.")

        if base == target:
            raise serializers.ValidationError("Base and target currencies cannot be the same.")

        # Update validated data dictionary with uppercase values
        data['base'] = base
        data['target'] = target
        return data


# ----------------------------
# FR1.2 – Rate Query Output
# ----------------------------

class LatestRateSerializer(serializers.Serializer):
    """
    Response serializer for rate lookup API.
    """
    base_currency = serializers.CharField(max_length=3)
    counter_currency = serializers.CharField(max_length=3)
    rate = serializers.DecimalField(max_digits=15, decimal_places=8)
    margin = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal(
            getattr(settings, 'CONVERSION_MARGIN', Decimal('0.00'))
        )
    )
    source = serializers.CharField(default="Redis Cache / PostgreSQL Fallback")
    fetched_at = serializers.DateTimeField()


# ----------------------------
# FR1.3 – Conversion Request Input (FIXED: Renamed fields to 'base' and 'target')
# ----------------------------

class ConversionRequestSerializer(serializers.Serializer):
    """
    Validates conversion request payload.
    """
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Amount to convert (e.g., 500.00)."
    )
    base = serializers.CharField(  # FIX: Renamed from 'from_currency'
        max_length=3,
        required=True,
        help_text="Source currency code (e.g., USD)."
    )
    target = serializers.CharField(  # FIX: Renamed from 'to_currency'
        max_length=3,
        required=True,
        help_text="Target currency code (e.g., NGN)."
    )

    def validate(self, data):
        """Ensure currency codes are uppercase and distinct."""
        # FIX: Changed key access from 'from_currency'/'to_currency' to 'base'/'target'
        base = data.get('base', '').upper()
        target = data.get('target', '').upper()

        if not base or not target:
            raise serializers.ValidationError("Both currency codes are required.")

        if base == target:
            raise serializers.ValidationError("Source and target currencies cannot be the same.")

        # Update validated data dictionary with uppercase values
        data['base'] = base
        data['target'] = target
        return data


# ----------------------------
# FR1.4 – Conversion Audit Output
# ----------------------------

class ConversionResponseSerializer(serializers.ModelSerializer):
    """
    Returns a successful conversion response (based on ConversionAudit model).
    """
    rate_id = serializers.UUIDField(source='rate_used_id', read_only=True)

    class Meta:
        model = ConversionAudit
        fields = (
            'id',
            'rate_id',
            'input_amount',
            'output_amount',
            'margin_applied',
            'converted_at',
        )
        read_only_fields = fields