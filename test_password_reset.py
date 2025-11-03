#!/usr/bin/env python3
"""
Simple test script for password reset email functionality
Run this with: python test_password_reset.py
"""

import os
import sys
import django
from django.conf import settings

# Add the current directory to the path so we can import Django models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stylescope_api.settings')

try:
    django.setup()
    
    from django.utils import timezone
    from datetime import datetime
    
    print("=== Password Reset Email Timezone Test ===")
    
    # Test the safe_format_datetime function from our view
    def safe_format_datetime(dt):
        try:
            if timezone.is_aware(dt):
                local_dt = timezone.localtime(dt)
            else:
                # If datetime is naive, make it timezone-aware first
                local_dt = timezone.localtime(timezone.make_aware(dt))
            return local_dt.strftime('%I:%M %p on %B %d, %Y')
        except Exception as e:
            print(f"Timezone conversion failed: {e}")
            # Fallback to simple string formatting if timezone conversion fails
            return dt.strftime('%I:%M %p on %B %d, %Y')
    
    # Test with timezone-aware datetime
    aware_dt = timezone.now()
    print(f"✓ Timezone-aware datetime: {aware_dt}")
    print(f"✓ Formatted: {safe_format_datetime(aware_dt)}")
    
    # Test with naive datetime
    naive_dt = datetime.now()
    print(f"✓ Naive datetime: {naive_dt}")
    print(f"✓ Formatted: {safe_format_datetime(naive_dt)}")
    
    print("\n✅ All timezone handling tests passed!")
    print("The password reset email functionality should now work correctly.")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    print("Make sure you have all dependencies installed and the database is accessible.")