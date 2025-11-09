#!/usr/bin/env python3
"""
Gmail API Status Checker for Stylescope
Run this to check if Gmail API is properly configured
"""

import os
import sys
import django
from django.conf import settings

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stylescope_api.settings')

try:
    django.setup()
    
    print("=== Gmail API Configuration Status ===")
    
    # Check email backend
    email_backend = getattr(settings, 'EMAIL_BACKEND', 'Not set')
    print(f"✓ Email Backend: {email_backend}")
    
    if 'gmailapi_backend' in email_backend:
        print("✓ Gmail API backend is configured")
        
        # Check required settings
        client_id = getattr(settings, 'GMAIL_API_CLIENT_ID', None)
        client_secret = getattr(settings, 'GMAIL_API_CLIENT_SECRET', None)
        refresh_token = getattr(settings, 'GMAIL_API_REFRESH_TOKEN', None)
        email_user = getattr(settings, 'EMAIL_HOST_USER', None)
        
        print(f"✓ Client ID: {client_id[:20]}..." if client_id else "❌ Client ID: Not set")
        print(f"✓ Client Secret: {client_secret[:10]}..." if client_secret and client_secret != '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' else "❌ Client Secret: Not set or using default")
        print(f"✓ Refresh Token: {refresh_token[:20]}..." if refresh_token and refresh_token != 'YOUR_REFRESH_TOKEN_GOES_HERE' else "❌ Refresh Token: Not set")
        print(f"✓ Email User: {email_user}" if email_user else "❌ Email User: Not set")
        
        if refresh_token and refresh_token != 'YOUR_REFRESH_TOKEN_GOES_HERE':
            print("\n✅ Gmail API appears to be fully configured!")
            print("🔗 Test by registering a user and checking email delivery")
        else:
            print("\n⚠️ Gmail API is partially configured")
            print("📋 Next steps:")
            print("   1. Visit: http://localhost:8000/api/v1/admin/gmail/oauth/start/")
            print("   2. Complete OAuth flow to get refresh token")
            print("   3. Update your environment variables")
    else:
        print("ℹ️ Using different email backend (not Gmail API)")
    
    # Test import
    try:
        import gmailapi_backend
        print("✓ gmailapi_backend package is installed")
    except ImportError:
        print("❌ gmailapi_backend package not installed")
        print("   Run: poetry install")
    
    print("\n=== Quick Test ===")
    print("To test email verification:")
    print("1. Start server: python manage.py runserver")
    print("2. Register user: POST /api/v1/auth/register/")
    print("3. Check email inbox for verification code")
    
except Exception as e:
    print(f"❌ Error checking Gmail API status: {e}")
    print("Make sure Django is properly configured and dependencies are installed")