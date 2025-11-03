# Email Configuration

This document explains how to configure email sending for password reset functionality.

## Development Setup (Console Backend)

By default, the application uses `console` email backend for development, which prints emails to the console instead of actually sending them.

## Production Setup (SMTP)

To actually send emails in production, set the following environment variables:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an "App Password" (not your regular Gmail password)
3. Use the app password as `EMAIL_HOST_PASSWORD`

### Other Email Providers

For other email providers, update the `EMAIL_HOST` and `EMAIL_PORT` accordingly:

- **Outlook/Hotmail**: 
  - HOST: `smtp.live.com`
  - PORT: `587`

- **Yahoo**: 
  - HOST: `smtp.mail.yahoo.com`
  - PORT: `587`

- **Custom SMTP**: Use your provider's SMTP settings

## Testing Email Functionality

To test the password reset email:

1. Start the Django server
2. Make a POST request to `/api/password-reset/request/` with:
   ```json
   {
     "email": "user@example.com"
   }
   ```
3. Check console output (development) or email inbox (production)

## Email Templates

The system uses two email templates:

- `api/templates/emails/password_reset.html` - HTML version
- `api/templates/emails/password_reset.txt` - Plain text version

Both templates support the same context variables:
- `user_name` - User's full name (if available)
- `email` - User's email address
- `reset_code` - 4-digit verification code
- `expiry_time` - When the code expires
- `timestamp` - When the code was generated

## Security Notes

- Reset codes expire after 15 minutes
- Codes are single-use only
- HTML email includes security warnings
- Failed email sending returns a 500 error with appropriate message