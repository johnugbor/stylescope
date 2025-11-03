from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from django.contrib.auth import authenticate
from .models import HumanModel, ClothingItem, Page, PageItem, EditJob, User, get_active_subscription, Support, SupportMessage, PasswordResetToken, EmailVerificationToken
from .utils import get_minio_url

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Check email verification before allowing login
        user = authenticate(username=attrs.get('email'), password=attrs.get('password'))
        if user and not user.is_email_verified:
            raise serializers.ValidationError({
                'email_verification': 'Please verify your email address before logging in. Check your email for the verification code.'
            })
        
        data = super().validate(attrs)
        
        # Get user's active subscription
        subscription = get_active_subscription(self.user)
        
        # Add user information and subscription data to the response
        data['user'] = {
            'email': self.user.email,
            'is_email_verified': self.user.is_email_verified,
            'subscription': {
                'has_active_subscription': subscription is not None,
                'remaining_credits': subscription.remaining_credits if subscription else 0,
                'plan_name': subscription.plan.name if subscription else None,
                'expires_at': subscription.end_date.isoformat() if subscription else None,
                'is_active': subscription.is_active() if subscription else False
            }
        }
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'is_email_verified')
        extra_kwargs = {
            'password': {'write_only': True},
            'is_email_verified': {'read_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        # Create email verification token after user creation
        EmailVerificationToken.create_for_user(user)
        return user

class HumanModelSerializer(serializers.ModelSerializer):
    display_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = HumanModel
        fields = ('id', 'user', 'name', 'image_url', 'display_image_url', 'is_selected', 'consent_given', 'created_at', 'updated_at')
        read_only_fields = ('user', 'display_image_url')
        
    def get_display_image_url(self, obj):
        # obj.image_url should contain only the object key
        return get_minio_url(obj.image_url, for_backend=False)
    
    def to_internal_value(self, data):
        # If image_url is provided and it's a full URL, extract just the object key
        if 'image_url' in data and data['image_url']:
            image_url = data['image_url']
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            # Check if it's a full MinIO URL and extract the object key
            if image_url.startswith('http') and f'/{bucket_name}/' in image_url:
                # Extract the object key part after the bucket name
                parts = image_url.split(f'/{bucket_name}/')
                if len(parts) > 1:
                    data['image_url'] = parts[1]
        
        return super().to_internal_value(data)        

class ClothingItemSerializer(serializers.ModelSerializer):
    full_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClothingItem
        fields = ('id', 'user', 'name', 'image_url', 'display_image_url', 'full_image_url', 'created_at', 'updated_at')
        read_only_fields = ('user', 'full_image_url')
        
    def get_display_image_url(self, obj):
        # obj.image_url should contain only the object key
        return get_minio_url(obj.image_url, for_backend=False)
    
    def get_edited_image_url(self, obj):
        # obj.display_image_url should contain only the object key
        return get_minio_url(obj.display_image_url, for_backend=False) if obj.display_image_url else None
    
    def get_full_image_url(self, obj):
        # obj.image_url should contain only the object key
        return get_minio_url(obj.image_url, for_backend=False) if obj.image_url else None

    def to_internal_value(self, data):
        # If image_url is provided and it's a full URL, extract just the object key
        if 'image_url' in data and data['image_url']:
            image_url = data['image_url']
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            # Check if it's a full MinIO URL and extract the object key
            if image_url.startswith('http') and f'/{bucket_name}/' in image_url:
                # Extract the object key part after the bucket name
                parts = image_url.split(f'/{bucket_name}/')
                if len(parts) > 1:
                    data['image_url'] = parts[1]
        
        return super().to_internal_value(data)
class PageItemSerializer(serializers.ModelSerializer):
    clothing_item = ClothingItemSerializer(read_only=True)
    clothing_item_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = PageItem
        fields = ('id', 'clothing_item', 'clothing_item_id', 'order_index')

class PageSerializer(serializers.ModelSerializer):
    items = PageItemSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = ('id', 'title', 'page', 'order_index', 'items')
        read_only_fields = ('user',)

class EditJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditJob
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information"""
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'email')  # Email cannot be changed via profile update

class SupportMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    
    class Meta:
        model = SupportMessage
        fields = ('id', 'message', 'message_type', 'sender_name', 'sender_email', 'created_at')
        read_only_fields = ('id', 'message_type', 'sender_name', 'sender_email', 'created_at')
    
    def get_sender_name(self, obj):
        if obj.sender.first_name or obj.sender.last_name:
            return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return obj.sender.email

class SupportSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Support
        fields = ('id', 'subject', 'status', 'user_name', 'user_email', 'message_count', 'messages', 'created_at', 'updated_at', 'closed_at')
        read_only_fields = ('id', 'user_name', 'user_email', 'message_count', 'messages', 'created_at', 'updated_at', 'closed_at')
    
    def get_user_name(self, obj):
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.email
    
    def get_message_count(self, obj):
        return obj.messages.count()

class CreateSupportMessageSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages in support tickets"""
    class Meta:
        model = SupportMessage
        fields = ('message',)
    
    def create(self, validated_data):
        # The support ticket and sender will be set in the view
        return super().create(validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset code"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value
    
    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # Create new reset token
        reset_token = PasswordResetToken.create_for_user(user)
        
        # Here you would send the email with the code
        # For now, we'll return the token so you can test it
        # In production, you should send an email and not return the code
        return reset_token


class PasswordResetVerifySerializer(serializers.Serializer):
    """Serializer for verifying reset code and setting new password"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=4, min_length=4)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 4 digits.")
        return value
    
    def validate(self, attrs):
        # Check if passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Verify the reset token
        email = attrs['email']
        code = attrs['code']
        
        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).first()
            
            if not reset_token:
                raise serializers.ValidationError("Invalid or expired reset code.")
            
            if not reset_token.is_valid():
                raise serializers.ValidationError("Reset code has expired.")
            
            attrs['reset_token'] = reset_token
            attrs['user'] = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid reset code.")
        
        return attrs
    
    def save(self):
        user = self.validated_data['user']
        reset_token = self.validated_data['reset_token']
        new_password = self.validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.mark_as_used()
        
        return user


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=4, min_length=4)
    
    def validate(self, attrs):
        email = attrs.get('email')
        code = attrs.get('code')
        
        try:
            user = User.objects.get(email=email)
            
            # Check if user is already verified
            if user.is_email_verified:
                raise serializers.ValidationError("Email is already verified.")
            
            # Find valid verification token
            verification_token = EmailVerificationToken.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).first()
            
            if not verification_token:
                raise serializers.ValidationError("Invalid verification code.")
            
            if not verification_token.is_valid():
                raise serializers.ValidationError("Verification code has expired. Please request a new one.")
            
            attrs['user'] = user
            attrs['verification_token'] = verification_token
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email address.")
        
        return attrs
    
    def save(self):
        user = self.validated_data['user']
        verification_token = self.validated_data['verification_token']
        
        # Mark user as verified
        user.is_email_verified = True
        user.save()
        
        # Mark token as used
        verification_token.mark_as_used()
        
        return user


class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            
            # Check if user is already verified
            if user.is_email_verified:
                raise serializers.ValidationError("Email is already verified.")
                
            return value
            
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
    
    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # Create new verification token
        verification_token = EmailVerificationToken.create_for_user(user)
        
        return verification_token