from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.middleware.csrf import get_token

# Create your views here.
@require_GET
def csrf_token_view(request):
    csrf_token = get_token(request)
    response = JsonResponse({'csrfToken': csrf_token})
    if not settings.DEBUG:
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            csrf_token,
            httponly=True,
            samesite='None',
            secure=True,
            max_age=31449600  # 1 year
        )
    return response

@method_decorator(csrf_exempt, name='dispatch')
class TestConnection(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        return Response({'connected': True})
    