# Gmail API Setup Guide for Stylescope

This guide will help you set up Gmail API for sending emails instead of using SMTP.

## Step 1: Install Required Packages

Run this command to install the necessary packages:

```bash
poetry install
```

This will install:
- `django-gmailapi-backend`
- `google-auth`
- `google-auth-oauthlib` 
- `google-auth-httplib2`
- `google-api-python-client`

## Step 2: Set Up Google Cloud Console

### 2.1 Create/Select Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your Project ID

### 2.2 Enable Gmail API
1. Go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click **Enable**

### 2.3 Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - Choose **External** user type
   - Fill in required fields:
     - App name: "Stylescope"
     - User support email: your email
     - Developer contact: your email
   - Add scopes: `https://www.googleapis.com/auth/gmail.send`
   - Add test users (your Gmail address)
4. For Application type, choose **Web application**
5. Add Authorized redirect URIs:
   ```
   http://localhost:8000/api/v1/admin/gmail/oauth/callback/
   http://127.0.0.1:8000/api/v1/admin/gmail/oauth/callback/
   ```
6. Click **Create**
7. Download the JSON file (credentials.json)

## Step 3: Get Refresh Token

### 3.1 Update Your Settings
Make sure your `settings.py` has the correct Client ID and Secret from the downloaded JSON:

```python
GMAIL_API_CLIENT_ID = 'your-client-id-here.apps.googleusercontent.com'
GMAIL_API_CLIENT_SECRET = 'your-client-secret-here'
```

### 3.2 Start Your Django Server
```bash
python manage.py runserver
```

### 3.3 Get OAuth Authorization
1. Visit: `http://localhost:8000/api/v1/admin/gmail/oauth/start/`
2. This will redirect you to Google OAuth consent screen
3. Sign in with the Gmail account you want to send emails from (`devjohnique@gmail.com`)
4. Grant permissions for Gmail sending
5. You'll be redirected back to your app with the refresh token

### 3.4 Update Environment Variables
After completing OAuth, update your `.env` file or environment variables:

```env
GMAIL_API_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GMAIL_API_CLIENT_SECRET=your-client-secret-here
GMAIL_API_REFRESH_TOKEN=the-refresh-token-you-got
EMAIL_HOST_USER=devjohnique@gmail.com
DEFAULT_FROM_EMAIL=devjohnique@gmail.com
```

## Step 4: Test Email Sending

### 4.1 Test with Registration
1. Register a new user via API:
```bash
POST /api/v1/auth/register/
{
  "email": "test@example.com",
  "password": "TestPass123!",
  "first_name": "Test",
  "last_name": "User"
}
```

2. Check the user's email inbox for verification code

### 4.2 Test Email Verification
```bash
POST /api/v1/auth/email-verification/verify/
{
  "email": "test@example.com", 
  "code": "1234"
}
```

## Step 5: Production Setup

### 5.1 Environment Variables
For production, set these environment variables:

```env
EMAIL_BACKEND=gmailapi_backend.mail.GmailBackend
GMAIL_API_CLIENT_ID=your-production-client-id
GMAIL_API_CLIENT_SECRET=your-production-client-secret
GMAIL_API_REFRESH_TOKEN=your-production-refresh-token
EMAIL_HOST_USER=your-production-email@gmail.com
DEFAULT_FROM_EMAIL=your-production-email@gmail.com
```

### 5.2 OAuth Consent Screen
For production:
1. Submit your OAuth consent screen for verification
2. Add production redirect URIs
3. Move from "Testing" to "Published" status

## Troubleshooting

### Common Issues

#### 1. "Access blocked: This app's request is invalid"
- Check redirect URIs match exactly
- Ensure Gmail API is enabled
- Verify OAuth consent screen is configured

#### 2. "Invalid client: no application name"
- Complete OAuth consent screen configuration
- Add app name and required fields

#### 3. "Refresh token not working"
- Re-run OAuth flow to get new refresh token
- Check token hasn't expired
- Verify scopes are correct

#### 4. "403 Forbidden" errors
- Check Gmail API is enabled
- Verify your project has quota
- Ensure correct permissions

### Debug Mode

To debug email issues, temporarily switch back to console backend:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

This will print emails to console instead of sending them.

## Security Notes

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate refresh tokens** periodically
4. **Limit OAuth scopes** to minimum required (`gmail.send`)
5. **Monitor API usage** in Google Cloud Console

## Benefits of Gmail API vs SMTP

- ✅ **No password/app passwords** needed
- ✅ **Better security** with OAuth 2.0
- ✅ **Higher rate limits** than SMTP
- ✅ **Better delivery rates**
- ✅ **Detailed error reporting**
- ✅ **No "less secure apps" issues**

Your Gmail API setup is now complete! The email verification system will use Gmail API to send professional verification emails.