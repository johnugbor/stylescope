from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_christmas import (ChristmasClothViewSet, MyPictureViewSet,
    CreditBundleViewSet, PaymentCodeVerifyView, CreditPurchaseView,
    ChristmasTryOnViewSet, CreditTransactionListView, christmas_pricing_info,
    PaystackPaymentInitiateView, get_payment_code, paystack_webhook
)

router = DefaultRouter()
router.register(r'clothes', ChristmasClothViewSet, basename='christmas-cloth')
router.register(r'my-pictures', MyPictureViewSet, basename='my-picture')
router.register(r'bundles', CreditBundleViewSet, basename='credit-bundle')
router.register(r'try-ons', ChristmasTryOnViewSet, basename='christmas-try-on')

urlpatterns = [
    # Authentication

    
    # Payment & Credits
    path('payment/verify/', PaymentCodeVerifyView.as_view(), name='payment-verify'),
    path('credits/purchase/', CreditPurchaseView.as_view(), name='credit-purchase'),
    path('credits/transactions/', CreditTransactionListView.as_view(), name='credit-transactions'),
    
    # Pricing
    path('pricing/', christmas_pricing_info, name='christmas-pricing'),
    
    # Paystack Payments
    path('payment/initiate/', PaystackPaymentInitiateView.as_view(), name='paystack-initiate'),
    path('payment/code/<str:reference>/', get_payment_code, name='get-payment-code'),
    path('payment/webhook/', paystack_webhook, name='paystack-webhook'),
    
    # Router URLs
    path('', include(router.urls)),
]
