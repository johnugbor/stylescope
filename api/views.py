import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .utils import send_email as gmail_send_email
# yourapp/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import os
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

from rest_framework_simplejwt.views import TokenObtainPairView
from .models import HumanModel, ClothingItem, Page, PageItem, EditJob, SubscriptionPlan, UserSubscription, get_active_subscription, Support, SupportMessage, PasswordResetToken, EmailVerificationToken
from .serializers import (
    HumanModelSerializer, ClothingItemSerializer, PageSerializer,
    PageItemSerializer, EditJobSerializer, UserSerializer, CustomTokenObtainPairSerializer,
    UserProfileSerializer, SupportSerializer, SupportMessageSerializer, CreateSupportMessageSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifySerializer, EmailVerificationSerializer, EmailVerificationResendSerializer
)
from .tasks import process_image_edit

User = get_user_model()
# User Registration
class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        
        # Send email verification after user creation
        verification_token = EmailVerificationToken.objects.filter(user=user, is_used=False).first()
        if verification_token:
            self.send_verification_email(user, verification_token)
    
    def send_verification_email(self, user, verification_token):
        """Send email verification email to user"""
        try:
            from django.utils import timezone
            
            # Get user info for the email
            user_name = f"{user.first_name} {user.last_name}".strip()
            if not user_name:
                user_name = None
            
            # Safely handle timezone formatting
            def safe_format_datetime(dt):
                try:
                    if timezone.is_aware(dt):
                        local_dt = timezone.localtime(dt)
                    else:
                        local_dt = timezone.localtime(timezone.make_aware(dt))
                    return local_dt.strftime('%I:%M %p on %B %d, %Y')
                except Exception:
                    return dt.strftime('%I:%M %p on %B %d, %Y')
            
            # Calculate expiry time for display
            expiry_time = safe_format_datetime(verification_token.expires_at)
            timestamp = safe_format_datetime(verification_token.created_at)
            
            # Prepare email context
            context = {
                'user_name': user_name,
                'email': user.email,
                'verification_code': verification_token.code,
                'expiry_time': expiry_time,
                'timestamp': timestamp,
            }
            
            # Render email templates
            html_message = render_to_string('emails/email_verification.html', context)
            plain_message = render_to_string('emails/email_verification.txt', context)
            
            # Send email using custom Gmail API
            success = gmail_send_email(
                to_email=user.email,
                subject='Stylescope - Email Verification Required',
                body=html_message,
                is_html=True
            )
            
            if not success:
                raise Exception("Failed to send email via Gmail API")
            
        except Exception as e:
            # Log the error (in production, use proper logging)
            print(f"Failed to send email verification: {str(e)}")
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        
        # Update response message to inform about email verification
        if response.status_code == 201:
            response.data.update({
                'message': 'Account created successfully! Please check your email for verification code.',
                'email_sent': True
            })
        
        return response

# User Login
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# Core ViewSets
class HumanModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HumanModelSerializer

    def get_queryset(self):
        return HumanModel.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        with transaction.atomic():
            HumanModel.objects.filter(user=request.user).update(is_selected=False)
            model = self.get_object()
            model.is_selected = True
            model.save()
        return Response(self.get_serializer(model).data)

class ClothingItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ClothingItemSerializer

    def get_queryset(self):
        return ClothingItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PageSerializer

    def get_queryset(self):
        queryset = Page.objects.filter(user=self.request.user).prefetch_related('items__clothing_item')
        
        # Filter by page number if provided
        page_number = self.request.query_params.get('page_number', None)
        if page_number is not None:
            queryset = queryset.filter(page=page_number)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='items')
    def add_item(self, request, pk=None):
        page = self.get_object()
        if page.items.count() >= 6:
            return Response({"error": "Page cannot have more than 6 items."}, status=status.HTTP_400_BAD_REQUEST)
        
        clothing_item_id = request.data.get('clothing_item_id')
        clothing_item = get_object_or_404(ClothingItem, id=clothing_item_id, user=request.user)
        
        # Default order_index is the current count
        order_index = page.items.count()
        page_item, created = PageItem.objects.get_or_create(
            page=page, 
            clothing_item=clothing_item,
            defaults={'order_index': order_index}
        )
        serializer = PageItemSerializer(page_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='auto-edit-all')
    def auto_edit_all_on_page(self, request, pk=None):
        page = self.get_object()
        items_count = page.items.count()
        
        if items_count == 0:
            return Response(
                {'error': 'No items found on this page to edit.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has active subscription with enough credits
        subscription = get_active_subscription(request.user)
        if not subscription:
            return Response(
                {'error': 'No active subscription found. Please upgrade your plan to use auto-edit features.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if subscription.remaining_credits < items_count:
            return Response(
                {'error': f'Insufficient credits. Need {items_count} credits but only {subscription.remaining_credits} available.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Consume credits for all items before starting the job
        try:
            remaining_credits = subscription.consume_credit(items_count)
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create and start the edit job
        job = EditJob.objects.create(user=request.user, job_type=EditJob.JobType.PAGE, page=page)
        process_image_edit.delay(job.id)
        
        return Response({
            'job_id': job.id, 
            'remaining_credits': remaining_credits,
            'items_processed': items_count,
            'message': f'Auto-edit started successfully. {items_count} credits consumed.'
        }, status=status.HTTP_202_ACCEPTED)

class PageItemViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='(?P<page_pk>[^/.]+)/items/(?P<item_pk>[^/.]+)/auto-edit')
    def auto_edit_single(self, request, page_pk=None, item_pk=None):
        page_item = get_object_or_404(PageItem, id=item_pk, page__id=page_pk, page__user=request.user)
        
        # Check if user has active subscription with credits
        subscription = get_active_subscription(request.user)
        if not subscription:
            return Response(
                {'error': 'No active subscription found. Please upgrade your plan to use auto-edit features.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if subscription.remaining_credits < 1:
            return Response(
                {'error': 'Insufficient credits. Please upgrade your plan or wait for renewal.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Consume 1 credit before starting the job
        try:
            remaining_credits = subscription.consume_credit(1)
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create and start the edit job
        job = EditJob.objects.create(user=request.user, job_type=EditJob.JobType.SINGLE, page_item=page_item)
        process_image_edit.delay(job.id)
        
        return Response({
            'job_id': job.id, 
            'remaining_credits': remaining_credits,
            'message': 'Auto-edit started successfully. 1 credit consumed.'
        }, status=status.HTTP_202_ACCEPTED)

# Global Job Endpoint
class GlobalEditView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Count total items across all user's pages
        total_items = PageItem.objects.filter(page__user=request.user).count()
        
        if total_items == 0:
            return Response(
                {'error': 'No items found to edit.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has active subscription with enough credits
        subscription = get_active_subscription(request.user)
        if not subscription:
            return Response(
                {'error': 'No active subscription found. Please upgrade your plan to use auto-edit features.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if subscription.remaining_credits < total_items:
            return Response(
                {'error': f'Insufficient credits. Need {total_items} credits but only {subscription.remaining_credits} available.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Consume credits for all items before starting the job
        try:
            remaining_credits = subscription.consume_credit(total_items)
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create and start the edit job
        job = EditJob.objects.create(user=request.user, job_type=EditJob.JobType.ALL)
        process_image_edit.delay(job.id)
        
        return Response({
            'job_id': job.id, 
            'remaining_credits': remaining_credits,
            'items_processed': total_items,
            'message': f'Global auto-edit started successfully. {total_items} credits consumed.'
        }, status=status.HTTP_202_ACCEPTED)

class JobViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EditJobSerializer

    def get_queryset(self):
        return EditJob.objects.filter(user=self.request.user).order_by('-created_at')

# Subscription Information Endpoint
class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current subscription and remaining credits"""
        subscription = get_active_subscription(request.user)
        
        if not subscription:
            return Response({
                'has_active_subscription': False,
                'remaining_credits': 0,
                'plan_name': None,
                'plan_credits': None,
                'expires_at': None,
                'is_active': False,
                'auto_renew': False,
                'message': 'No active subscription found.'
            })
        
        return Response({
            'has_active_subscription': True,
            'remaining_credits': subscription.remaining_credits,
            'plan_name': subscription.plan.name,
            'plan_credits': subscription.plan.credits,
            'plan_duration': subscription.plan.duration,
            'plan_price': float(subscription.plan.price),
            'expires_at': subscription.end_date.isoformat(),
            'is_active': subscription.is_active(),
            'auto_renew': subscription.auto_renew,
            'start_date': subscription.start_date.isoformat(),
            'revenuecat_id': subscription.revenuecat_id
        })

# File Upload View
class PresignUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        filename = request.data.get('filename')
        content_type = request.data.get('content_type')
        if not filename or not content_type:
            return Response({"error": "filename and content_type are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        object_name = f"uploads/{request.user.id}/{filename}"

        if settings.USE_S3:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(signature_version='s3v4')
            )
            try:
                response = s3_client.generate_presigned_post(
                    settings.AWS_STORAGE_BUCKET_NAME,
                    object_name,
                    Fields={'Content-Type': content_type},
                    Conditions=[{'Content-Type': content_type}],
                    ExpiresIn=3600
                )
                return Response(response)
            except ClientError as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # In local dev, we don't need a presigned URL, but we can simulate the structure.
            # The client will POST directly to a simple upload endpoint (not implemented for this MVP).
            # For KMM, it's easier to just have it always expect a presigned URL.
            # This part needs a local file upload handler if not using MinIO.
            return Response({"error": "Presigning is only available with S3/MinIO storage."}, status=status.HTTP_501_NOT_IMPLEMENTED)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def consume_credit(request):
    user = request.user
    subscription = get_active_subscription(user)

    if not subscription:
        return Response({"error": "No active subscription"}, status=403)

    try:
        remaining = subscription.consume_credit()
    except ValidationError as e:
        return Response({"error": str(e)}, status=400)

    return Response({
        "message": "Credit used successfully",
        "remaining_credits": remaining,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """Called manually or from RevenueCat webhook"""
    plan_id = request.data.get("plan_id")
    plan = SubscriptionPlan.objects.get(id=plan_id)
    user = request.user

    start_date = timezone.now()
    if plan.duration == "MONTHLY":
        end_date = start_date + timezone.timedelta(days=30)
    else:
        end_date = start_date + timezone.timedelta(days=365)

    sub = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=start_date,
        end_date=end_date,
        remaining_credits=plan.credits,
        auto_renew=True,
        active=True,
    )

    return Response({
        "message": f"{plan.name} subscription activated successfully",
        "remaining_credits": plan.credits,
        "auto_renew": sub.auto_renew,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def revenuecat_webhook(request):
    """
    Handles RevenueCat webhook events:
    - INITIAL_PURCHASE
    - RENEWAL
    - CANCELLATION
    - EXPIRATION
    """
    event = request.data.get("event")
    data = request.data.get("data", {})
    revenuecat_id = data.get("app_user_id")
    product_id = data.get("product_id")

    try:
        user = User.objects.get(email=revenuecat_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    try:
        plan = SubscriptionPlan.objects.get(name__iexact=product_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({"error": "Plan not found"}, status=404)

    # Find existing subscription
    sub = (
        UserSubscription.objects.filter(user=user, plan=plan)
        .order_by("-start_date")
        .first()
    )

    if event == "INITIAL_PURCHASE":
        if not sub or not sub.is_active():
            start_date = timezone.now()
            end_date = start_date + (
                timezone.timedelta(days=30)
                if plan.duration == "MONTHLY"
                else timezone.timedelta(days=365)
            )
            UserSubscription.objects.create(
                user=user,
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                remaining_credits=plan.credits,
                auto_renew=True,
                revenuecat_id=revenuecat_id,
            )

    elif event == "RENEWAL":
        if sub:
            sub.end_date += (
                timezone.timedelta(days=30)
                if plan.duration == "MONTHLY"
                else timezone.timedelta(days=365)
            )
            sub.remaining_credits = plan.credits
            sub.save()

    elif event in ["CANCELLATION", "EXPIRATION"]:
        if sub:
            sub.deactivate()

    return Response({"status": "success"})


# User Profile Management
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        """Update user profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Support Ticket System
class SupportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportSerializer
    
    def get_queryset(self):
        # Regular users only see their own tickets, admins see all
        if self.request.user.is_staff:
            queryset = Support.objects.all().prefetch_related('messages__sender')
        else:
            queryset = Support.objects.filter(user=self.request.user).prefetch_related('messages__sender')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status__iexact=status_filter)
        
        # Filter by minimum message count if provided
        min_message_count = self.request.query_params.get('min_message_count', None)
        if min_message_count:
            try:
                min_count = int(min_message_count)
                # Use annotations to count messages and filter
                from django.db.models import Count
                queryset = queryset.annotate(
                    message_count=Count('messages')
                ).filter(message_count__gte=min_count)
            except ValueError:
                pass  # Ignore invalid integer values
        
        # Filter to exclude tickets with no messages if specified
        has_messages = self.request.query_params.get('has_messages', None)
        if has_messages and has_messages.lower() in ['true', '1', 'yes']:
            from django.db.models import Count
            queryset = queryset.annotate(
                message_count=Count('messages')
            ).filter(message_count__gt=0)
        
        # Apply ordering (default: most recent first)
        ordering = self.request.query_params.get('ordering', '-created_at')
        valid_orderings = ['created_at', '-created_at', 'updated_at', '-updated_at', 'status', '-status']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')  # Default to newest first
        
        # Apply limit if provided
        limit = self.request.query_params.get('limit', None)
        if limit:
            try:
                limit_count = int(limit)
                if limit_count > 0:
                    queryset = queryset[:limit_count]
            except ValueError:
                pass  # Ignore invalid integer values
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a support ticket (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can close support tickets.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        support = self.get_object()
        if support.status == 'CLOSED':
            return Response(
                {'error': 'Support ticket is already closed.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        support.close(request.user)
        serializer = self.get_serializer(support)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message to the support ticket"""
        support = self.get_object()
        
        # Check if ticket is closed
        if support.status == 'CLOSED':
            return Response(
                {'error': 'Cannot send messages to a closed support ticket.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions - only ticket owner or admin can send messages
        if not request.user.is_staff and support.user != request.user:
            return Response(
                {'error': 'You can only send messages to your own support tickets.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateSupportMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(support=support, sender=request.user)
            
            # Return the created message with full details
            message_serializer = SupportMessageSerializer(serializer.instance)
            return Response(message_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a support ticket"""
        support = self.get_object()
        
        # Check permissions - only ticket owner or admin can view messages
        if not request.user.is_staff and support.user != request.user:
            return Response(
                {'error': 'You can only view messages from your own support tickets.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = support.messages.all()
        serializer = SupportMessageSerializer(messages, many=True)
        return Response(serializer.data)


# Password Reset System
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Request a password reset code"""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.save()
            
            # Send password reset email
            try:
                from django.utils import timezone
                
                # Get user info for the email
                user_name = f"{reset_token.user.first_name} {reset_token.user.last_name}".strip()
                if not user_name:
                    user_name = None
                
                # Safely handle timezone-aware and naive datetimes
                def safe_format_datetime(dt):
                    try:
                        if timezone.is_aware(dt):
                            local_dt = timezone.localtime(dt)
                        else:
                            # If datetime is naive, make it timezone-aware first
                            local_dt = timezone.localtime(timezone.make_aware(dt))
                        return local_dt.strftime('%I:%M %p on %B %d, %Y')
                    except Exception:
                        # Fallback to simple string formatting if timezone conversion fails
                        return dt.strftime('%I:%M %p on %B %d, %Y')
                
                # Calculate expiry time for display
                expiry_time = safe_format_datetime(reset_token.expires_at)
                timestamp = safe_format_datetime(reset_token.created_at)
                
                # Prepare email context
                context = {
                    'user_name': user_name,
                    'email': reset_token.user.email,
                    'reset_code': reset_token.code,
                    'expiry_time': expiry_time,
                    'timestamp': timestamp,
                }
                
                # Render email templates
                html_message = render_to_string('emails/password_reset.html', context)
                plain_message = render_to_string('emails/password_reset.txt', context)
                
                # Send email using custom Gmail API
                success = gmail_send_email(
                    to_email=reset_token.user.email,
                    subject=f'{reset_token.code} Stylescope - Password Reset Verification Code',
                    body=html_message,
                    is_html=True
                )
                
                if not success:
                    raise Exception("Failed to send email via Gmail API")
                
                return Response({
                    'message': 'Password reset code has been sent to your email.',
                    'expires_in_minutes': 15
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                # Log the error (in production, use proper logging)
                import traceback
                error_details = str(e)
                print(f"Failed to send password reset email: {error_details}")
                print(f"Traceback: {traceback.format_exc()}")
                
                return Response({
                    'error': 'Failed to send password reset email. Please try again later.',
                    'debug_message': error_details if settings.DEBUG else None  # Only show details in debug mode
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Verify reset code and set new password"""
        serializer = PasswordResetVerifySerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'message': 'Password has been reset successfully.',
                'email': user.email
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Utility view to check if reset code is valid (for testing)
class PasswordResetCheckView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Check if a reset code is valid (for testing purposes)"""
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({
                'error': 'Email and code are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).first()
            
            if not reset_token:
                return Response({
                    'valid': False,
                    'message': 'Invalid reset code.'
                })
            
            if not reset_token.is_valid():
                return Response({
                    'valid': False,
                    'message': 'Reset code has expired.'
                })
            
            return Response({
                'valid': True,
                'message': 'Reset code is valid.',
                'expires_at': reset_token.expires_at.isoformat()
            })
            
        except User.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'User not found.'
            })


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Verify email with 4-digit code"""
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'message': 'Email verified successfully! You can now log in.',
                'email': user.email,
                'is_email_verified': user.is_email_verified
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationResendView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Resend email verification code"""
        serializer = EmailVerificationResendSerializer(data=request.data)
        if serializer.is_valid():
            verification_token = serializer.save()
            
            # Send verification email
            try:
                self.send_verification_email(verification_token.user, verification_token)
                
                return Response({
                    'message': 'New verification code has been sent to your email.',
                    'expires_in_minutes': 30
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                # Log the error (in production, use proper logging)
                import traceback
                error_details = str(e)
                print(f"Failed to send verification email: {error_details}")
                print(f"Traceback: {traceback.format_exc()}")
                
                return Response({
                    'error': 'Failed to send verification email. Please try again later.',
                    'debug_message': error_details if settings.DEBUG else None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_verification_email(self, user, verification_token):
        """Send email verification email to user"""
        from django.utils import timezone
        
        # Get user info for the email
        user_name = f"{user.first_name} {user.last_name}".strip()
        if not user_name:
            user_name = None
        
        # Safely handle timezone formatting
        def safe_format_datetime(dt):
            try:
                if timezone.is_aware(dt):
                    local_dt = timezone.localtime(dt)
                else:
                    local_dt = timezone.localtime(timezone.make_aware(dt))
                return local_dt.strftime('%I:%M %p on %B %d, %Y')
            except Exception:
                return dt.strftime('%I:%M %p on %B %d, %Y')
        
        # Calculate expiry time for display
        expiry_time = safe_format_datetime(verification_token.expires_at)
        timestamp = safe_format_datetime(verification_token.created_at)
        
        # Prepare email context
        context = {
            'user_name': user_name,
            'email': user.email,
            'verification_code': verification_token.code,
            'expiry_time': expiry_time,
            'timestamp': timestamp,
        }
        
        # Render email templates
        html_message = render_to_string('emails/email_verification.html', context)
        plain_message = render_to_string('emails/email_verification.txt', context)
        
        # Send email using custom Gmail API
        success = gmail_send_email(
            to_email=user.email,
            subject=f'{verification_token.code} Stylescope - Email Verification Required',
            body=html_message,
            is_html=True
        )
        
        if not success:
            # Log the error but don't fail the verification token creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification email to {user.email} via Gmail API")
            
            # In development, print to console as fallback
            if settings.DEBUG:
                print(f"""
=== EMAIL VERIFICATION (Gmail API Failed) ===
To: {user.email}
Subject: Stylescope - Email Verification Required
Verification Code: {verification_token.code}
Expires: {expiry_time}
========================================
""")
            
            # Re-raise the exception if not in debug mode
            if not settings.DEBUG:
                raise





@staff_member_required
def gmail_oauth_start(request):
    """Start the OAuth flow."""
    # Hardcoded credentials - replace with your actual values from Google Cloud Console
    client_config = {
        "web": {
            "client_id":settings.GMAIL_CLIENT_ID,
            "client_secret":  settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GMAIL_OAUTH_CALLBACK_URL]
        }
    }
    
    # Create the flow from client config
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GMAIL_OAUTH_CALLBACK_URL
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent to get refresh token
    )
    
    # Save state in session
    request.session['gmail_oauth_state'] = state
    
    return redirect(authorization_url)


@staff_member_required
def gmail_oauth_callback(request):
    """Handle the OAuth callback."""
    try:
        state = request.session.get('gmail_oauth_state')
        
        # Same hardcoded credentials
        client_config = {
            "web": {
                "client_id":settings.GMAIL_CLIENT_ID,
                "client_secret":  settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GMAIL_OAUTH_CALLBACK_URL]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state,
            redirect_uri=settings.GMAIL_OAUTH_CALLBACK_URL
        )
        
        # Get the authorization response
        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        # Save the token - create directory if needed
        token_dir = os.path.join(settings.BASE_DIR, 'secrets')
        os.makedirs(token_dir, exist_ok=True)
        token_file = os.path.join(token_dir, 'gmail-token.json')
        
        with open(token_file, 'w') as token:
            token.write(credentials.to_json())
        try:
            os.chmod(token_file, 0o600)
        except:
            pass  # Might fail on Windows
        
        return render(request, 'admin/gmail_oauth_success.html', {
            'token_file': token_file,
        })
        
    except Exception as e:
        return render(request, 'admin/gmail_oauth_error.html', {
            'error': str(e)
        })


@staff_member_required
def gmail_oauth_status(request):
    """Check OAuth status."""
    token_exists = os.path.exists(settings.GMAIL_TOKEN_FILE)
    token_valid = False
    
    if token_exists:
        try:
            with open(settings.GMAIL_TOKEN_FILE, 'r') as token:
                token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                token_valid = creds and creds.valid
        except:
            pass
    
    return JsonResponse({
        'token_exists': token_exists,
        'token_valid': token_valid,
        'token_file': settings.GMAIL_TOKEN_FILE,
    })


class WaitlistNotificationView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated admin users
    
    def post(self, request):
        """Send Play Store notification to waitlist emails"""
        emails = request.data.get('emails', [])
        
        if not emails:
            return Response({
                'error': 'No email addresses provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(emails, list):
            return Response({
                'error': 'Emails must be provided as a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        successful_sends = 0
        failed_sends = 0
        errors = []
        
        for email in emails:
            try:
                # Validate email format
                from django.core.validators import validate_email
                validate_email(email)
                
                # Prepare email context
                context = {
                    'logo_url': 'https://stylescope-bucket.s3.amazonaws.com/uploads/10/Clothing_Item_1763126141776_1763126141777.jpg',
                    'playstore_url': 'https://play.google.com/store/apps/details?id=com.stylescope.android',
                    'app_name': 'Stylescope'
                }
                
                # Render email template
                html_message = render_to_string('emails/waitlist_notification.html', context)
                
                # Send email using custom Gmail API
                success = gmail_send_email(
                    to_email=email,
                    subject='🎉 Stylescope is now available on Google Play Store!',
                    body=html_message,
                    is_html=True
                )
                
                if success:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    errors.append(f"Failed to send to {email}")
                    
            except Exception as e:
                failed_sends += 1
                errors.append(f"Error sending to {email}: {str(e)}")
        
        return Response({
            'message': f'Waitlist notification process completed',
            'successful_sends': successful_sends,
            'failed_sends': failed_sends,
            'total_emails': len(emails),
            'errors': errors if errors else None
        }, status=status.HTTP_200_OK)
