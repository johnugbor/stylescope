# Email Verification System

This document explains the email verification system implemented for user registration.

## Overview

After user registration, users must verify their email address with a 4-digit code before they can log in to their account.

## Flow

1. **User Registration**: User creates account via `/api/auth/register/`
2. **Email Sent**: System automatically sends verification email with 4-digit code
3. **Email Verification**: User enters code via `/api/auth/email-verification/verify/`
4. **Login Enabled**: User can now log in with their email and password

## Database Changes

### User Model Updates
- Added `is_email_verified` field (default: `False`)
- Users cannot log in until this field is `True`

### New Model: EmailVerificationToken
- `user` - Foreign key to User
- `code` - 4-digit verification code
- `expires_at` - Token expiration (30 minutes)
- `is_used` - Single-use flag
- Inherits from BaseModel (UUID, timestamps)

## API Endpoints

### 1. User Registration
```
POST /api/auth/register/
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",  // optional
  "last_name": "Doe"     // optional
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_email_verified": false,
  "message": "Account created successfully! Please check your email for verification code.",
  "email_sent": true
}
```

### 2. Email Verification
```
POST /api/auth/email-verification/verify/
{
  "email": "user@example.com",
  "code": "1234"
}
```

**Response:**
```json
{
  "message": "Email verified successfully! You can now log in.",
  "email": "user@example.com",
  "is_email_verified": true
}
```

### 3. Resend Verification Code
```
POST /api/auth/email-verification/resend/
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "New verification code has been sent to your email.",
  "expires_in_minutes": 30
}
```

### 4. Login (Updated)
```
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response (Unverified User):**
```json
{
  "email_verification": ["Please verify your email address before logging in. Check your email for the verification code."]
}
```

**Response (Verified User):**
```json
{
  "access": "jwt_token",
  "refresh": "refresh_token",
  "user": {
    "email": "user@example.com",
    "is_email_verified": true,
    "subscription": { ... }
  }
}
```

## Email Templates

### HTML Email (`emails/email_verification.html`)
- Professional design with gradient styling
- Clear 4-digit code display
- Step-by-step instructions
- Security warnings
- Expiration information

### Plain Text Email (`emails/email_verification.txt`)
- Simple text version for clients that don't support HTML
- Same information as HTML version

## Security Features

- **4-digit codes**: Easy to enter, secure enough for email verification
- **30-minute expiration**: Reasonable time window for verification
- **Single-use tokens**: Codes become invalid after use
- **Token invalidation**: New requests invalidate old unused tokens
- **Login prevention**: Unverified users cannot log in
- **Email validation**: Proper email format validation

## Configuration

### Email Settings
Uses the same email configuration as password reset:
- Console backend for development (safe testing)
- SMTP backend for production
- Configurable via environment variables

### Timezone Handling
- Safe timezone conversion for email timestamps
- Fallback formatting if timezone operations fail
- Proper UTC/local time handling

## Error Handling

### Common Errors
- Invalid verification code
- Expired verification code
- Email already verified
- User not found
- Email sending failures

### Development vs Production
- Debug mode shows detailed error messages
- Production mode shows generic error messages
- Console logging for debugging email issues

## Testing

### Manual Testing Steps
1. Register new user
2. Check console/email for verification code
3. Attempt login without verification (should fail)
4. Verify email with code
5. Login successfully
6. Test expired code handling
7. Test resend functionality

### Edge Cases Covered
- Multiple verification requests
- Expired token handling
- Already verified users
- Invalid email addresses
- Email sending failures
- Timezone edge cases

## Migration

The system includes migration `0004_add_email_verification.py` that:
- Adds `is_email_verified` field to existing users (default: False)
- Creates `EmailVerificationToken` model
- Maintains data integrity

**Note**: Existing users will need to verify their email addresses or be manually marked as verified by an admin.