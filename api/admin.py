from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models.base import User
from .models.clothing import HumanModel, ClothingItem
from .models.pages import Page, PageItem
from .models.jobs import EditJob
from .models.Subscription import    UserSubscription,SubscriptionPlan
from .models.support import  Support,SupportMessage
from .models.christmas import (
    ChristmasUser, ChristmasCloth, MyPicture, CreditBundle,
    PaymentCode, ChristmasTryOn, CreditTransaction
)
class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active','is_email_verified')
    list_filter = ('is_staff', 'is_superuser', 'is_active','is_email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser','is_email_verified', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

@admin.register(HumanModel)
class HumanModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'is_selected', 'consent_given', 'created_at', 'updated_at')
    list_filter = ('is_selected', 'consent_given', 'created_at', 'updated_at')
    search_fields = ('name', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'user', 'image_url')
        }),
        ('Settings', {
            'fields': ('is_selected', 'consent_given')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at', 'updated_at', 'has_display_image')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def has_display_image(self, obj):
        return bool(obj.display_image_url)
    has_display_image.boolean = True
    has_display_image.short_description = 'Has Display Image'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'user')
        }),
        ('Images', {
            'fields': ('image_url', 'display_image_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'start_date', 'end_date', 'remaining_credits', 'active', 'auto_renew', 'is_active_status')
    list_filter = ('active', 'auto_renew', 'plan', 'start_date', 'end_date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'plan__name', 'revenuecat_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'is_active_status')
    ordering = ('-start_date',)
    
    def is_active_status(self, obj):
        return obj.is_active()
    is_active_status.boolean = True
    is_active_status.short_description = 'Currently Active'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'user', 'plan')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date', 'is_active_status')
        }),
        ('Credits & Settings', {
            'fields': ('remaining_credits', 'active', 'auto_renew')
        }),
        ('External Integration', {
            'fields': ('revenuecat_id',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'duration', 'price', 'credits', 'created_at', 'updated_at')
    list_filter = ('duration', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)

@admin.register(EditJob)
class EditJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'job_type', 'status', 'created_at', 'completed_at', 'has_result_image')
    list_filter = ('job_type', 'status', 'created_at', 'completed_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def has_result_image(self, obj):
        return bool(obj.result_image_url)
    has_result_image.boolean = True
    has_result_image.short_description = 'Has Result Image'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'user', 'job_type', 'status')
        }),
        ('Job Relations', {
            'fields': ('page_item', 'page')
        }),
        ('Results', {
            'fields': ('result_image_url', 'error_message')
        }),
        ('Timing', {
            'fields': ('created_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'page', 'created_at', 'updated_at', 'item_count')
    list_filter = ('page', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'item_count')
    ordering = ('-created_at',)
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Number of Items'

@admin.register(PageItem)
class PageItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'page', 'clothing_item', 'order_index', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at', 'page__page')
    search_fields = ('page__user__email', 'clothing_item__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Support)
class SupportAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'status', 'created_at', 'updated_at', 'message_count')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('user__email', 'subject', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'message_count')
    ordering = ('-created_at',)
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'

@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'support', 'sender', 'created_at', 'message_preview')
    list_filter = ('created_at', 'sender__is_staff')
    search_fields = ('support__subject', 'sender__email', 'message')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'

# ==================== CHRISTMAS MODULE ADMIN ====================

@admin.register(ChristmasUser)
class ChristmasUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'credits', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('id', 'password', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Account Info', {
            'fields': ('id', 'email', 'password', 'first_name', 'last_name')
        }),
        ('Credits & Status', {
            'fields': ('credits', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChristmasCloth)
class ChristmasClothAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'order_index', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'description', 'category')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('order_index', 'name')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'description', 'category')
        }),
        ('Image', {
            'fields': ('image_url',)
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order_index')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MyPicture)
class MyPictureAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_id', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('user__email', 'session_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(CreditBundle)
class CreditBundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'credits', 'price', 'discount_percentage', 'is_active', 'order_index')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('order_index', 'price')
    
    fieldsets = (
        ('Bundle Info', {
            'fields': ('id', 'name', 'credits', 'price', 'discount_percentage')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order_index')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentCode)
class PaymentCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'amount', 'credits', 'is_used', 'used_by', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('code', 'used_by__email', 'session_id')
    readonly_fields = ('id', 'code', 'is_used', 'used_by', 'used_at', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def save_model(self, request, obj, form, change):
        if not obj.code:
            obj.code = PaymentCode.generate_code()
        super().save_model(request, obj, form, change)


@admin.register(ChristmasTryOn)
class ChristmasTryOnAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_id', 'christmas_cloth', 'status', 'was_paid', 'created_at', 'completed_at')
    list_filter = ('status', 'was_paid', 'created_at', 'completed_at')
    search_fields = ('user__email', 'session_id', 'christmas_cloth__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Try-On Info', {
            'fields': ('id', 'user', 'session_id', 'christmas_cloth', 'my_picture')
        }),
        ('Status', {
            'fields': ('status', 'result_image_url', 'error_message')
        }),
        ('Payment', {
            'fields': ('payment_code', 'was_paid')
        }),
        ('Timing', {
            'fields': ('created_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'notes')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('id', 'user', 'transaction_type', 'amount', 'balance_after')
        }),
        ('Related Objects', {
            'fields': ('payment_code', 'credit_bundle', 'try_on')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(User, UserAdmin)