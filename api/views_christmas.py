from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import uuid

from .models.christmas import (
    ChristmasUser, ChristmasCloth, MyPicture, CreditBundle,
    PaymentCode, ChristmasTryOn, CreditTransaction
)
from .serializers_christmas import (
    ChristmasUserSerializer, ChristmasUserLoginSerializer,
    ChristmasClothSerializer, MyPictureSerializer, CreditBundleSerializer,
    PaymentCodeSerializer, PaymentCodeVerifySerializer,
    ChristmasTryOnSerializer, ChristmasTryOnCreateSerializer,
    CreditTransactionSerializer, CreditPurchaseSerializer
)
from .tasks import process_christmas_try_on  # We'll create this Celery task


# Custom Permission for Christmas Module
class IsChristmasUser(IsAuthenticated):
    """
    Custom permission to check if user is a ChristmasUser
    """
    def has_permission(self, request, view):
        # Check if user is authenticated via session
        return hasattr(request, 'christmas_user') and request.christmas_user is not None


# Authentication Middleware Helper
def get_christmas_user_from_request(request):
    """Helper to get ChristmasUser from session"""
    user_id = request.session.get('christmas_user_id')
    if user_id:
        try:
            return ChristmasUser.objects.get(id=user_id, is_active=True)
        except ChristmasUser.DoesNotExist:
            pass
    return None


# === AUTHENTICATION VIEWS ===

class ChristmasUserRegisterView(generics.CreateAPIView):
    """Register a new Christmas user"""
    permission_classes = [AllowAny]
    serializer_class = ChristmasUserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Log user in automatically after registration
        request.session['christmas_user_id'] = str(user.id)
        
        return Response({
            'message': 'Christmas account created successfully!',
            'user': ChristmasUserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class ChristmasUserLoginView(APIView):
    """Login for Christmas users"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ChristmasUserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        request.session['christmas_user_id'] = str(user.id)
        
        return Response({
            'message': 'Login successful!',
            'user': ChristmasUserSerializer(user).data
        })


class ChristmasUserLogoutView(APIView):
    """Logout Christmas user"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        if 'christmas_user_id' in request.session:
            del request.session['christmas_user_id']
        return Response({'message': 'Logout successful!'})


class ChristmasUserProfileView(APIView):
    """Get current Christmas user profile"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        christmas_user = get_christmas_user_from_request(request)
        if not christmas_user:
            return Response({
                'authenticated': False,
                'message': 'Not logged in'
            })
        
        return Response({
            'authenticated': True,
            'user': ChristmasUserSerializer(christmas_user).data
        })


# === CHRISTMAS CLOTHES VIEWS ===

class ChristmasClothViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve Christmas clothes (public)"""
    permission_classes = [AllowAny]
    serializer_class = ChristmasClothSerializer
    queryset = ChristmasCloth.objects.filter(is_active=True)


# === USER PICTURES VIEWS ===

class MyPictureViewSet(viewsets.ModelViewSet):
    """Manage user's uploaded pictures"""
    permission_classes = [AllowAny]
    serializer_class = MyPictureSerializer
    
    def get_queryset(self):
        christmas_user = get_christmas_user_from_request(self.request)
        session_id = self.request.session.session_key
        
        if christmas_user:
            return MyPicture.objects.filter(user=christmas_user)
        elif session_id:
            return MyPicture.objects.filter(session_id=session_id, user__isnull=True)
        return MyPicture.objects.none()
    
    def perform_create(self, serializer):
        christmas_user = get_christmas_user_from_request(self.request)
        session_id = self.request.session.session_key
        
        if not session_id:
            # Create a session if it doesn't exist
            self.request.session.create()
            session_id = self.request.session.session_key
        
        if christmas_user:
            serializer.save(user=christmas_user)
        else:
            serializer.save(session_id=session_id)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set a picture as primary"""
        picture = self.get_object()
        christmas_user = get_christmas_user_from_request(request)
        
        if christmas_user:
            # Unset other primary pictures
            MyPicture.objects.filter(user=christmas_user, is_primary=True).update(is_primary=False)
        
        picture.is_primary = True
        picture.save()
        
        return Response(self.get_serializer(picture).data)


# === CREDIT BUNDLES VIEWS ===

class CreditBundleViewSet(viewsets.ReadOnlyModelViewSet):
    """List available credit bundles"""
    permission_classes = [AllowAny]
    serializer_class = CreditBundleSerializer
    queryset = CreditBundle.objects.filter(is_active=True)


# === PAYMENT CODE VIEWS ===

class PaymentCodeVerifyView(APIView):
    """Verify and use a payment code"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PaymentCodeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code'].upper()
        christmas_user = get_christmas_user_from_request(request)
        session_id = request.data.get('session_id') or request.session.session_key
        
        try:
            with transaction.atomic():
                payment_code = PaymentCode.objects.select_for_update().get(code=code)
                
                if not payment_code.is_valid():
                    return Response({
                        'error': 'Payment code is invalid or already used.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Use the payment code
                credits = payment_code.use(user=christmas_user, session_id=session_id)
                
                # Create transaction record if user is logged in
                if christmas_user:
                    CreditTransaction.objects.create(
                        user=christmas_user,
                        transaction_type=CreditTransaction.TransactionType.PURCHASE,
                        amount=credits,
                        balance_after=christmas_user.credits,
                        payment_code=payment_code,
                        notes=f"Payment code {code} verified"
                    )
                
                return Response({
                    'message': 'Payment code verified successfully!',
                    'credits_added': credits,
                    'total_credits': christmas_user.credits if christmas_user else credits,
                    'payment_code_id': str(payment_code.id)
                })
        
        except PaymentCode.DoesNotExist:
            return Response({
                'error': 'Invalid payment code.'
            }, status=status.HTTP_400_BAD_REQUEST)


class CreditPurchaseView(APIView):
    """Purchase a credit bundle with payment code"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        christmas_user = get_christmas_user_from_request(request)
        
        if not christmas_user:
            return Response({
                'error': 'You must be logged in to purchase credit bundles.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = CreditPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        bundle_id = serializer.validated_data['bundle_id']
        code = serializer.validated_data['payment_code'].upper()
        
        try:
            with transaction.atomic():
                bundle = CreditBundle.objects.get(id=bundle_id, is_active=True)
                payment_code = PaymentCode.objects.select_for_update().get(code=code)
                
                # Verify payment amount matches bundle price
                if payment_code.amount < bundle.price:
                    return Response({
                        'error': f'Payment amount (${payment_code.amount}) is less than bundle price (${bundle.price}).'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if not payment_code.is_valid():
                    return Response({
                        'error': 'Payment code is invalid or already used.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Use payment code
                payment_code.use(user=christmas_user)
                
                # Add bundle credits
                christmas_user.add_credits(bundle.credits)
                
                # Create transaction record
                CreditTransaction.objects.create(
                    user=christmas_user,
                    transaction_type=CreditTransaction.TransactionType.PURCHASE,
                    amount=bundle.credits,
                    balance_after=christmas_user.credits,
                    payment_code=payment_code,
                    credit_bundle=bundle,
                    notes=f"Purchased {bundle.name}"
                )
                
                return Response({
                    'message': f'Successfully purchased {bundle.name}!',
                    'credits_added': bundle.credits,
                    'total_credits': christmas_user.credits,
                    'bundle': CreditBundleSerializer(bundle).data
                })
        
        except (CreditBundle.DoesNotExist, PaymentCode.DoesNotExist) as e:
            return Response({
                'error': 'Invalid bundle or payment code.'
            }, status=status.HTTP_400_BAD_REQUEST)


# === TRY-ON VIEWS ===

class ChristmasTryOnViewSet(viewsets.ModelViewSet):
    """Manage Christmas try-on jobs"""
    permission_classes = [AllowAny]
    serializer_class = ChristmasTryOnSerializer
    
    def get_queryset(self):
        christmas_user = get_christmas_user_from_request(self.request)
        session_id = self.request.session.session_key
        
        if christmas_user:
            return ChristmasTryOn.objects.filter(user=christmas_user)
        elif session_id:
            return ChristmasTryOn.objects.filter(session_id=session_id, user__isnull=True)
        return ChristmasTryOn.objects.none()
    
    def create(self, request, *args, **kwargs):
        serializer = ChristmasTryOnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        christmas_user = get_christmas_user_from_request(request)
        session_id = request.session.session_key
        
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        
        christmas_cloth = ChristmasCloth.objects.get(id=serializer.validated_data['christmas_cloth_id'])
        my_picture = MyPicture.objects.get(id=serializer.validated_data['my_picture_id'])
        
        # Check payment/credits
        payment_code_obj = serializer.validated_data.get('payment_code_obj')
        
        try:
            with transaction.atomic():
                # Logged in user
                if christmas_user:
                    # Option 1: Use existing credits
                    if christmas_user.has_credits(1):
                        christmas_user.consume_credits(1)
                        
                        try_on = ChristmasTryOn.objects.create(
                            user=christmas_user,
                            christmas_cloth=christmas_cloth,
                            my_picture=my_picture,
                            was_paid=False
                        )
                        
                        # Record transaction
                        CreditTransaction.objects.create(
                            user=christmas_user,
                            transaction_type=CreditTransaction.TransactionType.CONSUME,
                            amount=-1,
                            balance_after=christmas_user.credits,
                            try_on=try_on,
                            notes="Try-on created"
                        )
                    
                    # Option 2: Pay with payment code
                    elif payment_code_obj:
                        payment_code_obj.use(user=christmas_user, session_id=session_id)
                        
                        try_on = ChristmasTryOn.objects.create(
                            user=christmas_user,
                            christmas_cloth=christmas_cloth,
                            my_picture=my_picture,
                            payment_code=payment_code_obj,
                            was_paid=True
                        )
                    
                    else:
                        return Response({
                            'error': 'Insufficient credits. Please purchase credits or provide a payment code.'
                        }, status=status.HTTP_402_PAYMENT_REQUIRED)
                
                # Non-logged in user - must pay
                else:
                    if not payment_code_obj:
                        return Response({
                            'error': 'Payment code is required for non-logged in users.',
                            'hint': 'Register an account to buy credit bundles and save money!'
                        }, status=status.HTTP_402_PAYMENT_REQUIRED)
                    
                    payment_code_obj.use(session_id=session_id)
                    
                    try_on = ChristmasTryOn.objects.create(
                        session_id=session_id,
                        christmas_cloth=christmas_cloth,
                        my_picture=my_picture,
                        payment_code=payment_code_obj,
                        was_paid=True
                    )
                
                # Queue the try-on job
                process_christmas_try_on.delay(str(try_on.id))
                
                return Response({
                    'message': 'Christmas try-on started!',
                    'try_on': ChristmasTryOnSerializer(try_on).data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# === TRANSACTION HISTORY ===

class CreditTransactionListView(generics.ListAPIView):
    """List user's credit transaction history"""
    permission_classes = [AllowAny]
    serializer_class = CreditTransactionSerializer
    
    def get_queryset(self):
        christmas_user = get_christmas_user_from_request(self.request)
        if christmas_user:
            return CreditTransaction.objects.filter(user=christmas_user)
        return CreditTransaction.objects.none()


# === PRICING INFO ===

@api_view(['GET'])
@permission_classes([AllowAny])
def christmas_pricing_info(request):
    """Get pricing information for the Christmas try-on feature"""
    single_price = 2.99  # Price per single try-on
    bundles = CreditBundle.objects.filter(is_active=True)
    
    return Response({
        'single_try_on_price': single_price,
        'currency': 'USD',
        'bundles': CreditBundleSerializer(bundles, many=True).data,
        'benefits': {
            'registered_users': [
                'Buy credit bundles and save up to 50%',
                'Track your try-on history',
                'Save your favorite pictures',
                'No need to pay for each try-on'
            ],
            'guest_users': [
                'Pay per try-on',
                'Instant access, no registration needed'
            ]
        }
    })
