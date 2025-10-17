from django.urls import path
# We import RateQueryAPIView and ConversionAPIView, matching the names in views.py
from .views import RateQueryAPIView, ConversionAPIView, RegisterAPIView 

# Define the app namespace
app_name = 'exchange_app'

urlpatterns = [
    path('rate/', RateQueryAPIView.as_view(), name='fx-rate-query'), 
    path('convert/', ConversionAPIView.as_view(), name='currency-convert'),
    path('register/', RegisterAPIView.as_view(), name='register'),
]