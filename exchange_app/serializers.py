from rest_framework import serializers
from decimal import Decimal
from django.conf import settings
from exchange_app.models import ConversionAudit, ExchangeRate

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
        base = data.get('base', '').upper()
        target = data.get('target', '').upper()
        if not base or not target:
            raise serializers.ValidationError("Both currency codes are required.")
        if base == target:
            raise serializers.ValidationError("Base and target currencies cannot be the same.")
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
        base = data.get('base', '').upper()
        target = data.get('target', '').upper()
        if not base or not target:
            raise serializers.ValidationError("Both currency codes are required.")
        if base == target:
            raise serializers.ValidationError("Source and target currencies cannot be the same.")
        data['base'] = base
        data['target'] = target
        return data

# ----------------------------
# FR1.4 – Conversion Audit Output
# ----------------------------
class ExchangeRateSerializer(serializers.ModelSerializer):
    """
    Serializer for the ExchangeRate model to nest in ConversionResponseSerializer.
    """
    class Meta:
        model = ExchangeRate
        fields = ['base_currency', 'counter_currency', 'rate_value', 'fetched_at']

class ConversionResponseSerializer(serializers.ModelSerializer):
    """
    Returns a successful conversion response (based on ConversionAudit model).
    """
    rate_used = ExchangeRateSerializer()  # Nest the related ExchangeRate object
    effective_rate = serializers.SerializerMethodField()  # Compute effective rate dynamically

    class Meta:
        model = ConversionAudit
        fields = (
            'id',
            'rate_used',
            'input_amount',
            'output_amount',
            'margin_applied',
            'converted_at',
            'effective_rate',
        )
        read_only_fields = fields

    def get_effective_rate(self, obj):
        """
        Compute the effective rate based on the rate used and margin applied.
        Note: This is a placeholder; the actual rate is calculated in the view.
        """
        # Since effective_rate isn't stored, we rely on the view to provide it
        # This method will be overridden by the view's response_data
        rate_value = obj.rate_used.rate_value
        margin = obj.margin_applied
        return float(rate_value * (Decimal('1.0') - margin))