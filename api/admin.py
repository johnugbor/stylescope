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

admin.site.register(User, UserAdmin)
admin.site.register(HumanModel)
admin.site.register(ClothingItem)
admin.site.register(Page)
admin.site.register(PageItem)
admin.site.register(EditJob)
admin.site.register(UserSubscription)
admin.site.register(SubscriptionPlan)
admin.site.register(Support)
admin.site.register(SupportMessage)