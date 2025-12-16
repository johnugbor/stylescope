from rest_framework import serializers
from .models.christmas import (
    ChristmasUser, ChristmasCloth, MyPicture, CreditBundle,
    PaymentCode, ChristmasTryOn, CreditTransaction
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class ChristmasUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = ChristmasUser
        fields = ['id', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'credits', 'created_at']
        read_only_fields = ['id', 'credits', 'created_at']
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = ChristmasUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChristmasUserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        try:
            user = ChristmasUser.objects.get(email=email, is_active=True)
        except ChristmasUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        
        attrs['user'] = user
        return attrs


class ChristmasClothSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChristmasCloth
        fields = ['id', 'name', 'description', 'image_url', 'category', 'is_active', 'order_index', 'created_at']
        read_only_fields = ['id', 'created_at']


class MyPictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyPicture
        fields = ['id', 'image_url', 'is_primary', 'created_at']
        read_only_fields = ['id', 'is_primary', 'created_at']


class CreditBundleSerializer(serializers.ModelSerializer):
    savings = serializers.SerializerMethodField()
    price_per_credit = serializers.SerializerMethodField()
    
    class Meta:
        model = CreditBundle
        fields = ['id', 'name', 'credits', 'price', 'discount_percentage', 'savings', 'price_per_credit', 'is_active']
        read_only_fields = ['id']
    
    def get_savings(self, obj):
        """Calculate savings amount"""
        if obj.discount_percentage > 0:
            original_price = float(obj.price) / (1 - obj.discount_percentage / 100)
            return round(original_price - float(obj.price), 2)
        return 0
    
    def get_price_per_credit(self, obj):
        """Calculate price per credit"""
        if obj.credits > 0:
            return round(float(obj.price) / obj.credits, 2)
        return 0


class PaymentCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCode
        fields = ['id', 'code', 'amount', 'credits', 'is_used', 'expires_at', 'created_at']
        read_only_fields = ['id', 'code', 'is_used', 'created_at']


class PaymentCodeVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    session_id = serializers.CharField(max_length=100, required=False)
    
    def validate_code(self, value):
        try:
            payment_code = PaymentCode.objects.get(code=value.upper())
        except PaymentCode.DoesNotExist:
            raise serializers.ValidationError("Invalid payment code.")
        
        if not payment_code.is_valid():
            if payment_code.is_used:
                raise serializers.ValidationError("Payment code has already been used.")
            else:
                raise serializers.ValidationError("Payment code has expired.")
        
        return value


class ChristmasTryOnSerializer(serializers.ModelSerializer):
    christmas_cloth_details = ChristmasClothSerializer(source='christmas_cloth', read_only=True)
    my_picture_details = MyPictureSerializer(source='my_picture', read_only=True)
    
    class Meta:
        model = ChristmasTryOn
        fields = [
            'id', 'christmas_cloth', 'christmas_cloth_details', 
            'my_picture', 'my_picture_details',
            'status', 'result_image_url', 'error_message',
            'was_paid', 'completed_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'result_image_url', 'error_message', 'was_paid', 'completed_at', 'created_at']


class ChristmasTryOnCreateSerializer(serializers.Serializer):
    christmas_cloth_id = serializers.UUIDField()
    my_picture_id = serializers.UUIDField()
    payment_code = serializers.CharField(max_length=50, required=False)
    session_id = serializers.CharField(max_length=100, required=False)
    
    def validate_christmas_cloth_id(self, value):
        try:
            cloth = ChristmasCloth.objects.get(id=value, is_active=True)
        except ChristmasCloth.DoesNotExist:
            raise serializers.ValidationError("Christmas cloth not found or not active.")
        return value
    
    def validate_my_picture_id(self, value):
        try:
            picture = MyPicture.objects.get(id=value)
        except MyPicture.DoesNotExist:
            raise serializers.ValidationError("Picture not found.")
        return value
    
    def validate(self, attrs):
        # Validate payment code if provided
        if attrs.get('payment_code'):
            try:
                payment_code = PaymentCode.objects.get(code=attrs['payment_code'].upper())
                if not payment_code.is_valid():
                    raise serializers.ValidationError({"payment_code": "Payment code is invalid or already used."})
                attrs['payment_code_obj'] = payment_code
            except PaymentCode.DoesNotExist:
                raise serializers.ValidationError({"payment_code": "Invalid payment code."})
        
        return attrs


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'balance_after',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CreditPurchaseSerializer(serializers.Serializer):
    bundle_id = serializers.UUIDField()
    payment_code = serializers.CharField(max_length=50)
    
    def validate_bundle_id(self, value):
        try:
            bundle = CreditBundle.objects.get(id=value, is_active=True)
        except CreditBundle.DoesNotExist:
            raise serializers.ValidationError("Credit bundle not found or not active.")
        return value
    
    def validate_payment_code(self, value):
        try:
            payment_code = PaymentCode.objects.get(code=value.upper())
            if not payment_code.is_valid():
                if payment_code.is_used:
                    raise serializers.ValidationError("Payment code has already been used.")
                else:
                    raise serializers.ValidationError("Payment code has expired.")
        except PaymentCode.DoesNotExist:
            raise serializers.ValidationError("Invalid payment code.")
        return value
