from django.urls import path
# We import RateQueryAPIView and ConversionAPIView, matching the names in views.py
from .views import RateQueryAPIView, ConversionAPIView 

# Define the app namespace
app_name = 'exchange_app'

urlpatterns = [
    # Uses the correct view class name: RateQueryAPIView
    # Note: Your view file comment suggested a path like '/api/v1/rates/latest/', 
    # so I've updated the path() here to 'rate/'. 
    path('rate/', RateQueryAPIView.as_view(), name='fx-rate-query'),
    
    # Uses the correct view class name: ConversionAPIView
    # Note: Your view file comment suggested a path like '/api/v1/conversions/', 
    # so I've updated the path() here to 'convert/'. 
    path('convert/', ConversionAPIView.as_view(), name='currency-convert'),
]