from celery import shared_task
from django.db import transaction, DatabaseError
from django.utils import timezone
from .api_client import CurrencyExchangeAPIClient, ExternalAPIError
from .models import ExchangeRate
from logging import getLogger
from decimal import Decimal
from typing import Dict, List

logger = getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # Retry after 5 minutes
    queue='rate_updates'
)
def fetch_and_save_latest_rates(self):
    """
    Fetches the latest exchange rates from the external API and saves them to the database.
    Ensures atomicity, retries on transient errors, and logs all major operations.
    """
    logger.info("Starting fetch_and_save_latest_rates task execution.")
    
    try:
        client = CurrencyExchangeAPIClient()
        rates: Dict[str, Decimal] = client.fetch_latest_rates()
        # Access the instance variable 'base_currency' (which was fixed in the last step)
        base_currency = client.base_currency
        timestamp = timezone.now()

        # Determine the provider name robustly
        provider_name = getattr(client, 'provider_name', getattr(client, 'PROVIDER_NAME', 'UnknownFX'))
        
        with transaction.atomic():
            rate_objects: List[ExchangeRate] = []

            for counter_currency, rate_value in rates.items():
                if rate_value <= Decimal('0'):
                    logger.warning(
                        f"Skipping invalid rate for {base_currency}/{counter_currency}. Value: {rate_value}"
                    )
                    continue

                rate_objects.append(
                    ExchangeRate(
                        base_currency=base_currency,
                        counter_currency=counter_currency,
                        rate_value=rate_value, 
                        fetched_at=timestamp, 
                        # Use the determined provider_name variable
                        provider_name=provider_name
                    )
                )

            ExchangeRate.objects.bulk_create(rate_objects)

        logger.info(f"✅ Successfully committed {len(rate_objects)} exchange rates to the database.")
        
        # Signal success
        return f"Successfully committed {len(rate_objects)} exchange rates."


    except ExternalAPIError as e:
        logger.error(f"External FX API failed (Attempt {self.request.retries + 1}/{self.max_retries}): {e}")
        raise self.retry(exc=e)

    except DatabaseError as e:
        logger.critical(f"Database error during rate saving: {e}")
        raise self.retry(exc=e)

    except Exception as e:
        logger.critical(f"A critical, unrecoverable error occurred in rate fetching task: {e}")
        raise