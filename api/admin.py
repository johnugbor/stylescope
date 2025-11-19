from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models.base import User
from .models.clothing import HumanModel, ClothingItem
from .models.pages import Page, PageItem
from .models.jobs import EditJob
from .models.Subscription import    UserSubscription,SubscriptionPlan
from .models.support import  Support,SupportMessage
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

admin.site.register(User, UserAdmin)