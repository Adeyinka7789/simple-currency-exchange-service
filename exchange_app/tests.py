from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from decimal import Decimal, ROUND_HALF_UP

from exchange_app.models import ExchangeRate, ConversionAudit
# Assuming your ExchangeRate model has these attributes.
# If your ExchangeRate model requires 'rate_source' or other fields, 
# you'll need to update the setUp method below.

# --- Test Constants ---
BASE_RATE_URL = reverse('exchange_app:fx-rate-query')
CONVERSION_URL = reverse('exchange_app:currency-convert')

MOCK_BASE = 'USD'
MOCK_TARGET = 'NGN'
MOCK_RATE_VALUE = Decimal('1250.00000000') # Matches the rate inserted previously
MOCK_MARGIN = Decimal('0.005')
INPUT_AMOUNT = Decimal('100.00')

class ExchangeAPITestCase(TestCase):
    """
    Base test case setup for creating required mock data.
    """
    def setUp(self):
        self.client = APIClient()
        self.now = timezone.now()

        # Create a mock ExchangeRate record for testing successful queries
        self.mock_rate = ExchangeRate.objects.create(
            base_currency=MOCK_BASE,
            counter_currency=MOCK_TARGET,
            rate_value=MOCK_RATE_VALUE,
            fetched_at=self.now,
            # If your model requires 'rate_source', uncomment and define it:
            # rate_source='TEST_MOCK' 
        )

# ----------------------------------------------------------------------
# 1. RateQueryAPIView Tests (GET /api/rate/)
# ----------------------------------------------------------------------

class RateQueryAPIViewTest(ExchangeAPITestCase):
    
    def test_successful_rate_query_200_ok(self):
        """
        Tests successful retrieval of the latest exchange rate.
        """
        response = self.client.get(BASE_RATE_URL, {'base': MOCK_BASE, 'target': MOCK_TARGET})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['base_currency'], MOCK_BASE)
        self.assertEqual(response.data['counter_currency'], MOCK_TARGET)
        # Check that the rate matches the mock data
        self.assertEqual(Decimal(response.data['rate']), MOCK_RATE_VALUE)
        self.assertEqual(Decimal(response.data['margin']), MOCK_MARGIN)


    def test_rate_query_not_found_404(self):
        """
        Tests the case where an exchange rate for a specific pair does not exist.
        """
        # Query a currency pair that was NOT created in setUp
        response = self.client.get(BASE_RATE_URL, {'base': 'EUR', 'target': 'JPY'})
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("No valid exchange rate found for EUR/JPY", response.data['error'])


    def test_rate_query_missing_params_400_bad_request(self):
        """
        Tests validation failure when required query parameters are missing.
        """
        # 1. Missing 'target'
        response_missing_target = self.client.get(BASE_RATE_URL, {'base': MOCK_BASE})
        self.assertEqual(response_missing_target.status_code, 400)
        self.assertIn('target', response_missing_target.data['error'])
        
        # 2. Missing 'base'
        response_missing_base = self.client.get(BASE_RATE_URL, {'target': MOCK_TARGET})
        self.assertEqual(response_missing_base.status_code, 400)
        self.assertIn('base', response_missing_base.data['error'])

# ----------------------------------------------------------------------
# 2. ConversionAPIView Tests (POST /api/convert/)
# ----------------------------------------------------------------------

class ConversionAPIViewTest(ExchangeAPITestCase):

    def test_successful_conversion_200_ok(self):
        """
        Tests successful currency conversion, calculation, and audit creation.
        """
        payload = {
            "amount": str(INPUT_AMOUNT),
            "base": MOCK_BASE,
            "target": MOCK_TARGET
        }
        
        # Perform the POST request
        response = self.client.post(CONVERSION_URL, payload, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # 1. Check Audit Record Creation
        self.assertTrue(ConversionAudit.objects.filter(id=response.data['id']).exists())
        audit_record = ConversionAudit.objects.get(id=response.data['id'])
        
        # 2. Check Conversion Calculation
        
        # Rate with spread: 1250.00 * (1 - 0.005) = 1243.75
        adjusted_rate = MOCK_RATE_VALUE * (Decimal('1.0') - MOCK_MARGIN)
        # Expected output: 100.00 * 1243.75 = 124375.00
        expected_output = (INPUT_AMOUNT * adjusted_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        self.assertEqual(audit_record.output_amount, expected_output)
        self.assertEqual(Decimal(response.data['output_amount']), expected_output)
        self.assertEqual(Decimal(response.data['margin_applied']), MOCK_MARGIN)


    def test_conversion_rate_not_found_404(self):
        """
        Tests the case where a rate exists, but not for the requested conversion pair.
        """
        payload = {
            "amount": "100.00",
            "base": "EUR", # Rate not in database
            "target": "JPY"  # Rate not in database
        }
        response = self.client.post(CONVERSION_URL, payload, format='json')
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("No current rate available for EUR/JPY", response.data['error'])


    def test_conversion_missing_fields_400_bad_request(self):
        """
        Tests validation failure when required fields in the payload are missing.
        """
        # Missing 'amount'
        payload_missing_amount = {
            "base": MOCK_BASE,
            "target": MOCK_TARGET
        }
        response = self.client.post(CONVERSION_URL, payload_missing_amount, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('amount', response.data['error'])

        # Missing 'target'
        payload_missing_target = {
            "amount": "100.00",
            "base": MOCK_BASE
        }
        response = self.client.post(CONVERSION_URL, payload_missing_target, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('target', response.data['error'])