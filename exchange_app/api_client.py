import requests
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class ExternalAPIError(Exception):
    """Custom exception for errors returned by the external FX API."""
    pass

class CurrencyExchangeAPIClient:
    """
    Client for interacting with the external currency exchange rate API (ExchangesRateAPI.com).
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initializes the client with API key and base URL from Django settings.
        """
        self.api_key = api_key if api_key is not None else settings.FX_API_KEY
        self.base_url = base_url if base_url is not None else settings.FX_API_BASE_URL
        self.base_currency = 'EUR'
        self.provider_name = settings.FX_PROVIDER_NAME

    def _make_request(self, endpoint: str = '', params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generic method to handle API requests, error checking, and response parsing.
        """
        url = f"{self.base_url}{endpoint}"
        
        request_params = {
            'apiKey': self.api_key,  # Correct param for exchangesrateapi.com
        }
        
        if params:
            request_params.update(params)
            
        try:
            logger.info(f"Making request to: {url} with params: {request_params}")
            response = requests.get(url, params=request_params, timeout=10)
            
            # Log raw response for debugging
            logger.debug(f"Raw response: {response.text[:500]}")
            
            response.raise_for_status()
            data = response.json()
            
            # Check for error field (exchangesrateapi.com format)
            if 'error' in data:
                raise ExternalAPIError(f"API returned error: {data.get('error', 'Unknown error')}")
                
            return data
            
        except requests.exceptions.HTTPError as e:
            error_message = f"{e.response.status_code} Client Error: {e.response.reason} for url: {e.request.url}"
            logger.error(f"External FX API failed: {error_message}")
            raise ExternalAPIError(f"A connection error occurred while reaching the FX API: {error_message}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected request error occurred for {url}: {e}")
            raise ExternalAPIError(f"An unexpected request error occurred: {e}") from e
        except ValueError as e:
            logger.error(f"JSON decode error for {url}: {e} - Response: {response.text[:500]}")
            raise ExternalAPIError(f"JSON decode error: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred processing API response: {e}")
            raise ExternalAPIError(f"An unexpected error occurred: {e}") from e

    def fetch_latest_rates(self) -> Dict[str, Decimal]:
        """
        Fetches the latest exchange rates relative to the base currency (EUR).
        Returns: A dictionary of {currency_code: rate (Decimal)}.
        """
        logger.info("Fetching latest exchange rates from external API.")
        
        data = self._make_request(endpoint='')  # Base URL has /api/latest
        
        # Ensure rates data is present
        if 'rates' not in data or not isinstance(data['rates'], dict):
            raise ExternalAPIError("API response missing 'rates' data.")
        
        rates = {
            currency: Decimal(str(rate))
            for currency, rate in data['rates'].items()
        }
        
        logger.info(f"Successfully fetched {len(rates)} exchange rates.")
        return rates

    def check_api_status(self) -> bool:
        """
        Attempts a basic request to verify the API key and connection are working.
        """
        try:
            self.fetch_latest_rates()
            return True
        except ExternalAPIError as e:
            logger.warning(f"API status check failed: {e}")
            return False