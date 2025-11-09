from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HumanModelViewSet, ClothingItemViewSet, PageViewSet, PageItemViewSet,
    JobViewSet, PresignUploadView, RegisterView, GlobalEditView, SubscriptionView,
    UserProfileView, SupportViewSet, PasswordResetRequestView, PasswordResetVerifyView, PasswordResetCheckView,
    EmailVerificationView, EmailVerificationResendView,
    consume_credit, create_subscription, revenuecat_webhook,gmail_oauth_start, gmail_oauth_callback, gmail_oauth_status 
)

router = DefaultRouter()
router.register(r'human-models', HumanModelViewSet, basename='humanmodel')
router.register(r'clothes', ClothingItemViewSet, basename='clothingitem')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'support', SupportViewSet, basename='support')

urlpatterns = [
    path('', include(router.urls)),
    path('storage/presign/', PresignUploadView.as_view(), name='presign-upload'),
    path('auto-edit-all-pages/', GlobalEditView.as_view(), name='auto-edit-all'),
    path('subscription/', SubscriptionView.as_view(), name='subscription-info'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Password Reset endpoints
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('auth/password-reset/check/', PasswordResetCheckView.as_view(), name='password-reset-check'),
    
    # Email Verification endpoints
    path('auth/email-verification/verify/', EmailVerificationView.as_view(), name='email-verification-verify'),
    path('auth/email-verification/resend/', EmailVerificationResendView.as_view(), name='email-verification-resend'),
    
    # This nested route is tricky for standard routers, handled via a custom action
    path('pages/<uuid:page_pk>/items/<uuid:item_pk>/auto-edit/', 
         PageItemViewSet.as_view({'post': 'auto_edit_single'}), name='auto-edit-single'),
    path("consume-credit/", consume_credit, name="consume_credit"),
    path("create-subscription/", create_subscription, name="create_subscription"),
    path("revenuecat-webhook/", revenuecat_webhook, name="revenuecat_webhook"),
    path('admin/gmail/oauth/start/', gmail_oauth_start, name='gmail_oauth_start'),
    path('admin/gmail/oauth/callback/', gmail_oauth_callback, name='gmail_oauth_callback'),
    path('admin/gmail/oauth/status/', gmail_oauth_status, name='gmail_oauth_status'),
]



