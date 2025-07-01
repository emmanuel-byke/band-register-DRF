from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTAuthFromCookie(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("access_token")
        if token is None:
            return None
        validated_token = self.get_validated_token(token)
        return self.get_user(validated_token), validated_token
