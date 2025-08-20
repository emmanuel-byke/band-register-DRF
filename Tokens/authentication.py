# tokens/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions
import logging

logger = logging.getLogger(__name__)

class JWTAuthFromCookie(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from cookies
    and handles CSRF protection for state-changing operations
    """
    
    def authenticate(self, request):
        # Get token from cookie
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None
            
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            
            # For state-changing operations, enforce CSRF protection
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                self.enforce_csrf(request)
            
            return (user, validated_token)
            
        except TokenError as e:
            logger.debug(f"Token validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in JWT authentication: {str(e)}")
            return None
    
    def enforce_csrf(self, request):
        """
        Enforce CSRF protection for authenticated requests
        """
        def dummy_get_response(request):
            return None
        
        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')
    
    def authenticate_header(self, request):
        return 'Bearer'