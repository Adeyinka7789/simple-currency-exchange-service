import uuid
from decimal import Decimal
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

# --- CUSTOM MANAGER FOR OPTIMIZED RATE LOOKUP ---
class ExchangeRateManager(models.Manager):
    """
    Custom manager to efficiently retrieve the latest exchange rate for a pair.
    It checks Redis cache first (high performance) before falling back to the DB.
    Supports inverse rate calculation for non-EUR base currencies using EUR as pivot.
    """
    def get_latest_rate(self, base_currency: str, counter_currency: str):
        """
        Retrieves the latest rate from Redis or PostgreSQL, handling inverse rates.
        Since all rates are stored with EUR as base, we pivot through EUR for non-EUR bases.
        """
        cache_key = f"fx_rate:{base_currency}:{counter_currency}"
        
        # Try fetching from Redis cache
        rate_data = cache.get(cache_key)
        
        if rate_data:
            return rate_data
        
        try:
            # Case 1: Direct rate if base is EUR
            if base_currency == 'EUR':
                latest_rate = self.filter(
                    base_currency=base_currency,
                    counter_currency=counter_currency,
                ).order_by('-fetched_at').first()
                
                if latest_rate:
                    cache.set(cache_key, latest_rate.rate_value, timeout=65 * 60)
                    return latest_rate.rate_value
            
            # Case 2: Pivot through EUR for non-EUR base
            base_to_eur = self.filter(
                base_currency='EUR',
                counter_currency=base_currency,
            ).order_by('-fetched_at').first()
            
            if not base_to_eur:
                raise self.model.DoesNotExist(f"No rate found for EUR/{base_currency}")
            
            eur_to_target = self.filter(
                base_currency='EUR',
                counter_currency=counter_currency,
            ).order_by('-fetched_at').first()
            
            if not eur_to_target:
                raise self.model.DoesNotExist(f"No rate found for EUR/{counter_currency}")
            
            # Calculate base to target via EUR: (1 / EUR→base) * EUR→target
            base_to_eur_rate = base_to_eur.rate_value
            eur_to_target_rate = eur_to_target.rate_value
            rate_value = (Decimal('1.0') / base_to_eur_rate * eur_to_target_rate).quantize(Decimal('0.0001'))
            
            cache.set(cache_key, rate_value, timeout=65 * 60)
            return rate_value
        
        except self.model.DoesNotExist as e:
            raise
        except Exception as e:
            logger.error(f"CRITICAL DB ERROR during rate lookup: {e}")
            raise self.model.DoesNotExist("A database error occurred during rate retrieval.")
        
# --- IMMUTABLE EXCHANGE RATE MODEL (FR1.1 & FR1.2) ---
class ExchangeRate(models.Model):
    """
    Stores an immutable record of a specific exchange rate at a specific time.
    Used for historical data and linking to ConversionAudit records.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Currency codes should be standardized (e.g., ISO 4217, 3 characters)
    base_currency = models.CharField(max_length=3, db_index=True)
    counter_currency = models.CharField(max_length=3, db_index=True)
    
    # High precision Decimal field for rates (Integrity requirement)
    rate_value = models.DecimalField(max_digits=15, decimal_places=8)
    
    provider_name = models.CharField(max_length=50, default=settings.FX_PROVIDER_NAME)
    
    # Timestamp when the rate was fetched (Immutability/Auditability)
    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Attach the custom manager
    objects = ExchangeRateManager()
    
    class Meta:
        ordering = ['-fetched_at']
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        # Unique constraint on currency pairs at a specific time prevents duplicate ingestion
        unique_together = ('base_currency', 'counter_currency', 'fetched_at')
    
    def __str__(self):
        return f"1 {self.base_currency} = {self.rate_value} {self.counter_currency} ({self.fetched_at.date()})"

# --- IMMUTABLE CONVERSION AUDIT MODEL (FR1.4) ---
class ConversionAudit(models.Model):
    """
    An immutable log of every currency conversion transaction performed by the API.
    Crucial for financial reconciliation and auditability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Crucial FK link to the specific immutable rate record used (Auditability)
    rate_used = models.ForeignKey(
        ExchangeRate,
        on_delete=models.PROTECT,
        related_name='audits',
        verbose_name="Rate Record Used"
    )
    
    # The actual amount the client requested to convert
    input_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # The final amount returned to the client after conversion and margin
    output_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Record the margin applied at the time of conversion for full transparency
    margin_applied = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal(0))
    
    # Timestamp of the conversion request
    converted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-converted_at']
        verbose_name = "Conversion Audit"
        verbose_name_plural = "Conversion Audits"
    
    def __str__(self):
        return (
            f"Audit {self.id.hex[:6]}: {self.input_amount} {self.rate_used.base_currency} "
            f"-> {self.output_amount} {self.rate_used.counter_currency}"
        )