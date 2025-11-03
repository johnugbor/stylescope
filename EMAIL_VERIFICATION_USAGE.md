# Email Verification API Usage

Simple usage examples for the email verification endpoints in Stylescope API.

## Base URL
```
http://localhost:8000/api/v1
```

## 1. User Registration (Triggers Email Verification)

```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_email_verified": false,
  "message": "Account created successfully! Please check your email for verification code.",
  "email_sent": true
}
```

**Note:** Check your Django console for the 4-digit verification code (since you're using console email backend).

## 2. Email Verification

```http
POST /api/v1/auth/email-verification/verify/
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "1234"
}
```

**Success Response (200):**
```json
{
  "message": "Email verified successfully! You can now log in.",
  "email": "user@example.com",
  "is_email_verified": true
}
```

**Error Responses:**

Invalid code (400):
```json
{
  "non_field_errors": ["Invalid verification code."]
}
```

Expired code (400):
```json
{
  "non_field_errors": ["Verification code has expired. Please request a new one."]
}
```

Already verified (400):
```json
{
  "non_field_errors": ["Email is already verified."]
}
```

## 3. Resend Verification Code

```http
POST /api/v1/auth/email-verification/resend/
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "message": "New verification code has been sent to your email.",
  "expires_in_minutes": 30
}
```

**Error Responses:**

Already verified (400):
```json
{
  "email": ["Email is already verified."]
}
```

User not found (400):
```json
{
  "email": ["No account found with this email address."]
}
```

## Testing Flow

1. **Register user** → Get verification code from console
2. **Verify email** → User can now login
3. **Try resend** → Should work if not verified, fail if already verified

## Console Output Example

After registration, check your Django server console for:
```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Stylescope - Email Verification Required
From: your-email@gmail.com
To: user@example.com

STYLESCOPE - Email Verification Required

Welcome John!

Your email verification code is: 1234

This code will expire in 30 minutes...
```

Copy the 4-digit code and use it in the verification endpoint.