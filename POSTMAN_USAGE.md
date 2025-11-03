# Stylescope API - Postman Usage Examples

This document provides complete Postman examples for testing the Stylescope API, including the new email verification system.

## Base Configuration

**Base URL:** `http://localhost:8000/api/v1` (adjust for your environment)

**Headers for all requests:**
```
Content-Type: application/json
Accept: application/json
```

## 1. User Registration with Email Verification

### Register New User
```http
POST {{base_url}}/auth/register/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Expected Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_email_verified": false,
  "message": "Account created successfully! Please check your email for verification code.",
  "email_sent": true
}
```

**What happens:**
- User account is created but `is_email_verified = false`
- 4-digit verification code is sent to email (check console in development)
- User cannot log in until email is verified

## 2. Email Verification Process

### Verify Email with Code
```http
POST {{base_url}}/auth/email-verification/verify/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "code": "1234"
}
```

**Expected Response (200 OK):**
```json
{
  "message": "Email verified successfully! You can now log in.",
  "email": "john.doe@example.com",
  "is_email_verified": true
}
```

**Error Response - Invalid Code (400 Bad Request):**
```json
{
  "non_field_errors": ["Invalid verification code."]
}
```

**Error Response - Expired Code (400 Bad Request):**
```json
{
  "non_field_errors": ["Verification code has expired. Please request a new one."]
}
```

### Resend Verification Code
```http
POST {{base_url}}/auth/email-verification/resend/
Content-Type: application/json

{
  "email": "john.doe@example.com"
}
```

**Expected Response (200 OK):**
```json
{
  "message": "New verification code has been sent to your email.",
  "expires_in_minutes": 30
}
```

**Error Response - Already Verified (400 Bad Request):**
```json
{
  "email": ["Email is already verified."]
}
```

## 3. Login Process

### Attempt Login (Unverified User)
```http
POST {{base_url}}/auth/login/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```

**Error Response (400 Bad Request):**
```json
{
  "email_verification": ["Please verify your email address before logging in. Check your email for the verification code."]
}
```

### Successful Login (Verified User)
```http
POST {{base_url}}/auth/login/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```

**Expected Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "email": "john.doe@example.com",
    "is_email_verified": true,
    "subscription": {
      "has_active_subscription": false,
      "remaining_credits": 0,
      "plan_name": null,
      "expires_at": null,
      "is_active": false
    }
  }
}
```

## 4. Password Reset (Existing Feature)

### Request Password Reset
```http
POST {{base_url}}/auth/password-reset/request/
Content-Type: application/json

{
  "email": "john.doe@example.com"
}
```

**Expected Response (200 OK):**
```json
{
  "message": "Password reset code has been sent to your email.",
  "expires_in_minutes": 15
}
```

### Verify Password Reset Code
```http
POST {{base_url}}/auth/password-reset/verify/
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "code": "5678",
  "new_password": "NewSecurePass123!"
}
```

**Expected Response (200 OK):**
```json
{
  "message": "Password reset successfully. You can now log in with your new password."
}
```

## 5. Authenticated Requests

For all authenticated endpoints, include the JWT token in the Authorization header:

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Get User Profile
```http
GET {{base_url}}/profile/
Authorization: Bearer {{access_token}}
```

### Upload Human Model
```http
POST {{base_url}}/human-models/
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "name": "My Model",
  "image_url": "path/to/image.jpg",
  "consent_given": true
}
```

## 6. Postman Environment Variables

Create a Postman environment with these variables:

```json
{
  "base_url": "http://localhost:8000/api/v1",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "access_token": "",
  "refresh_token": ""
}
```

## 7. Postman Collection Structure

### Folder: Authentication
- Register User
- Verify Email
- Resend Verification Code
- Login
- Password Reset Request
- Password Reset Verify

### Folder: User Management
- Get Profile
- Update Profile

### Folder: Virtual Try-On
- Upload Human Model
- Upload Clothing Item
- Create Page
- Auto Edit Single Item
- Auto Edit All Pages

## 8. Testing Workflow

### Complete Registration Flow:
1. **Register** → Creates unverified user
2. **Check Console** → Copy 4-digit verification code
3. **Verify Email** → Activates account
4. **Login** → Gets JWT tokens
5. **Save Tokens** → Store in environment variables
6. **Test Protected Endpoints** → Use Bearer token

### Test Error Cases:
1. **Invalid verification code** → Should return 400
2. **Expired verification code** → Should return 400
3. **Login without verification** → Should return 400
4. **Already verified email** → Should return 400
5. **Invalid email format** → Should return 400

## 9. Development vs Production

### Development (Console Backend)
- Emails are printed to console
- Check Django server logs for verification codes
- No actual email sending required

### Production (SMTP Backend)
- Real emails are sent
- Check user's email inbox
- Configure SMTP settings in environment variables

## 10. Common Issues & Solutions

### Issue: "Email verification required"
**Solution:** Complete email verification before login

### Issue: "Verification code expired"
**Solution:** Request new code via resend endpoint

### Issue: "Invalid verification code"
**Solution:** Check console logs for correct code

### Issue: "Email already verified"
**Solution:** User can proceed to login

### Issue: "User not found"
**Solution:** Verify email address is correct

## 11. Pre-request Scripts (Postman)

### Auto-extract tokens after login:
```javascript
if (responseCode.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set("access_token", jsonData.access);
    pm.environment.set("refresh_token", jsonData.refresh);
}
```

### Auto-set email verification code:
```javascript
// Use this in console to extract verification code
// Look for: "Your email verification code is: 1234"
// Then manually set in environment or copy to request
```

## 12. Status Codes Summary

- **200 OK** - Successful operations
- **201 Created** - User registration successful
- **400 Bad Request** - Validation errors, unverified email
- **401 Unauthorized** - Invalid/missing authentication
- **404 Not Found** - User/resource not found
- **500 Internal Server Error** - Email sending failures

This Postman collection covers the complete user journey from registration through email verification to authenticated API usage.