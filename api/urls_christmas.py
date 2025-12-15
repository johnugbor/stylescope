from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_christmas import (
    ChristmasUserRegisterView, ChristmasUserLoginView, ChristmasUserLogoutView,
    ChristmasUserProfileView, ChristmasClothViewSet, MyPictureViewSet,
    CreditBundleViewSet, PaymentCodeVerifyView, CreditPurchaseView,
    ChristmasTryOnViewSet, CreditTransactionListView, christmas_pricing_info
)

router = DefaultRouter()
router.register(r'clothes', ChristmasClothViewSet, basename='christmas-cloth')
router.register(r'my-pictures', MyPictureViewSet, basename='my-picture')
router.register(r'bundles', CreditBundleViewSet, basename='credit-bundle')
router.register(r'try-ons', ChristmasTryOnViewSet, basename='christmas-try-on')

urlpatterns = [
    # Authentication
    path('auth/register/', ChristmasUserRegisterView.as_view(), name='christmas-register'),
    path('auth/login/', ChristmasUserLoginView.as_view(), name='christmas-login'),
    path('auth/logout/', ChristmasUserLogoutView.as_view(), name='christmas-logout'),
    path('auth/profile/', ChristmasUserProfileView.as_view(), name='christmas-profile'),
    
    # Payment & Credits
    path('payment/verify/', PaymentCodeVerifyView.as_view(), name='payment-verify'),
    path('credits/purchase/', CreditPurchaseView.as_view(), name='credit-purchase'),
    path('credits/transactions/', CreditTransactionListView.as_view(), name='credit-transactions'),
    
    # Pricing
    path('pricing/', christmas_pricing_info, name='christmas-pricing'),
    
    # Router URLs
    path('', include(router.urls)),
]
