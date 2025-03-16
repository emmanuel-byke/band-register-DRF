from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework.authtoken.models import Token

class TokenRenewalMiddleware:
    """
    Middleware to automatically renew tokens when they're about to expire
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if user is authenticated via token
        if hasattr(request, 'auth') and isinstance(request.auth, Token):
            token = request.auth
            
            # Calculate when the token should be renewed (e.g., when it has less than 7 days left)
            renewal_date = token.created + timedelta(seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS) - timedelta(days=7)
            
            # If token is approaching expiry, update its creation date
            if renewal_date <= timezone.now():
                token.created = timezone.now()
                token.save()
        
        return response