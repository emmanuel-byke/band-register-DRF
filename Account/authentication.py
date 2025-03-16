# Account/authentication.py
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Token authentication with expiry functionality.
    Tokens expire after TOKEN_EXPIRED_AFTER_SECONDS (defaults to 60 days)
    """
    
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        
        # Check if token is expired
        expiry_date = token.created + timedelta(seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS)
        
        if expiry_date < timezone.now():
            token.delete()
            raise AuthenticationFailed('Token has expired')
        
        return user, token