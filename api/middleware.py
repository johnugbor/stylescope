from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models.christmas import ChristmasUser


class ChristmasUserMiddleware(MiddlewareMixin):
    """
    Middleware to set request.christmas_user from JWT token or session
    """
    def process_request(self, request):
        # First try to get from session
        user_id = request.session.get('christmas_user_id')
        if user_id:
            try:
                request.christmas_user = ChristmasUser.objects.get(id=user_id, is_active=True)
                return
            except ChristmasUser.DoesNotExist:
                pass
        
        # If not in session, try JWT token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                request.christmas_user = ChristmasUser.objects.get(id=user_id, is_active=True)
            except (InvalidToken, TokenError, ChristmasUser.DoesNotExist, KeyError):
                pass
        else:
            request.christmas_user = None