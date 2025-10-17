from django.contrib import admin
from .models import ExchangeRate, ConversionAudit


# --- Custom Admin for ExchangeRate ---
@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    """
    Admin interface for immutable ExchangeRate records.
    Rates are read-only and ordered by insertion time (newest first).
    """
    list_display = (
        'id',
        'base_currency',
        'counter_currency',  # Fixed field name
        'rate_value',
        'provider_name',
        'fetched_at'
    )
    list_filter = ('provider_name', 'base_currency', 'counter_currency')
    search_fields = ('base_currency', 'counter_currency', 'provider_name')

    # Make all fields read-only
    readonly_fields = list_display

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# --- Custom Admin for ConversionAudit ---
@admin.register(ConversionAudit)
class ConversionAuditAdmin(admin.ModelAdmin):
    """
    Admin interface for immutable ConversionAudit records.
    Displays a complete audit trail with related ExchangeRate details.
    """
    list_display = (
        'id',
        'input_amount',
        'get_base_currency',      # Custom field
        'output_amount',
        'get_counter_currency',   # Custom field
        'margin_applied',
        'rate_used_id',
        'converted_at'
    )
    list_filter = ('rate_used__base_currency', 'rate_used__counter_currency', 'converted_at')
    search_fields = ('rate_used__base_currency', 'rate_used__counter_currency', 'id')
    date_hierarchy = 'converted_at'

    # Displayed fields on the detail page
    fields = (
        'id',
        'rate_used',
        'input_amount',
        'get_base_currency',
        'output_amount',
        'get_counter_currency',
        'margin_applied',
        'converted_at'
    )

    readonly_fields = fields

    # Custom field methods
    @admin.display(description="From Currency")
    def get_base_currency(self, obj):
        return obj.rate_used.base_currency if obj.rate_used else "-"

    @admin.display(description="To Currency")
    def get_counter_currency(self, obj):
        return obj.rate_used.counter_currency if obj.rate_used else "-"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False