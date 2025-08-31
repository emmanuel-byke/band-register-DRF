from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import UserSerializer, UserCreateSerializer, PublicUserSerializer, AuthTokenSerializer
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.conf import settings
from rest_framework.authtoken.views import ObtainAuthToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.middleware.csrf import get_token
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.request.user.is_admin:
            return User.objects.all()
        return User.objects.filter(username=self.request.user.username)
    
    @action(detail=True, methods=['post'])
    def add_division(self, request, pk=None):
        """
        POST /users/{user_id}/add_division/
        Expects JSON: { "division_id": <id> }
        """
        from Data.models import Division
        
        user = self.get_object()
        division_id = request.data.get('division_id')
        try:
            division = Division.objects.get(pk=division_id)
        except Division.DoesNotExist:
            return Response({'detail': 'Division not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.divisions.add(division)
        return Response({'detail': 'Division added successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_division(self, request, pk=None):
        """
        POST /users/{user_id}/remove_division/
        Expects JSON: { "division_id": <id> }
        """
        from Data.models import Division
        
        user = self.get_object()
        division_id = request.data.get('division_id')
        try:
            division = Division.objects.get(pk=division_id)
        except Division.DoesNotExist:
            return Response({'detail': 'Division not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.divisions.remove(division)
        return Response({'detail': 'Division removed successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def get_users(self, request):        
        user = self.get_object()
        serializer = PublicUserSerializer(user, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='permissions')
    def change_user_permissions(self, request, pk=None):
        request_id = request.data.get('request_id')
        if request_id is not None:
            user = User.objects.get(id=pk)
            active = request.data.get('activate')
            admin = request.data.get('admin')
            if active is not None:
                user.is_active = active
            if admin is not None:
                user.is_admin = admin
                print('changing admin status:', admin)
            user.save()
                
            return Response({'sucess': True, 'user': PublicUserSerializer(user, many=False).data})
        return Response({'sucess': False})
    
    @action(detail=False, methods=['get'])
    def top_attendance(self, request):
        max_users = int(request.data.get('max_users', 5))
        
        # Get top users with total attendance annotation
        top_users = User.objects.annotate(
            total_attendance=Coalesce(Sum('divisions__attendance__attendance'), Value(0))
        ).order_by('-total_attendance')[:max_users]
        
        # Get all user stats with proper annotations
        all_user_stat = User.objects.annotate(
            attendance=Coalesce(Sum('divisions__attendance__attendance'), Value(0)),
            sessions=Coalesce(Sum('divisions__attendance__sessions'), Value(0)),
            absent=Coalesce(Sum('divisions__absent__sessions'), Value(0))
        )  # Removed incorrect ordering
        
        # Calculate totals using aggregate instead of looping
        totals = all_user_stat.aggregate(
            total_attendance=Sum('attendance'),
            total_sessions=Sum('sessions'),
            total_absent=Sum('absent')
        )
        
        return Response({
            'top': [{
                'name': f'{user.fname[0]}. {user.lname}',
                'total_attendance': user.total_attendance
            } for user in top_users],
            'attendance': totals['total_attendance'] or 0,
            'sessions': (totals['total_sessions'] or 0) + (totals['total_absent'] or 0),
            'active_users': User.objects.filter(is_active=True).count(),
        })
    
class PublicUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = [permissions.AllowAny]


def set_auth_cookies(response, user, request=None):
    """Set JWT tokens and CSRF token in cookies"""
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    csrf_token = get_token(request) if request else None

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Set to False for development if not using HTTPS
        samesite="None",
        max_age=60 * 15,  # 15 minutes
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Set to False for development if not using HTTPS
        samesite="None",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )

    # Set CSRF token cookie
    if csrf_token:
        response.set_cookie(
            key="csrftoken",
            value=csrf_token,
            httponly=False,
            secure=True,  # Set to False for development if not using HTTPS
            samesite="None",
            max_age=24 * 60 * 60,  # 24 hours
        )

    return response

@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """Get CSRF token endpoint"""
    csrf_token = get_token(request)
    return Response({'csrfToken': csrf_token})


    
# @method_decorator(csrf_exempt, name='dispatch')
@permission_classes([AllowAny])
class SignupView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        user = serializer.save()
        if User.objects.count() == 1:
            user.is_admin = True
            user.save(update_fields=['is_admin'])
    
    def create(self, request, *args, **kwargs):
        print(request.data)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
        except IntegrityError as e:
            error_messages = {
                'username': 'A user with that username already exists.',
            }
            for field, message in error_messages.items():
                if field in str(e).lower():
                    return Response(
                        {field: [message]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(
                {'detail': 'Could not create user due to a conflict.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Refresh user to include is_admin changes
        user = serializer.instance
        user.refresh_from_db()

        response =  Response({ 'user': UserSerializer(user, context=self.get_serializer_context()).data })
        return set_auth_cookies(response, user, request)
        
        
# @method_decorator(csrf_exempt, name='dispatch')
@permission_classes([AllowAny])
class LoginView(ObtainAuthToken):
    """Custom login view to return auth token and user info"""
    serializer_class = AuthTokenSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=401)
        else:
            user.logged_in_times += 1
            user.save(update_fields=['logged_in_times'])

        response = Response({ 'user': UserSerializer(user).data})
        return set_auth_cookies(response, user, request)
        

# @method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """Logout view that clears cookies"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get refresh token and blacklist it
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            logger.error(f"Error blacklisting token: {str(e)}")
        
        response = Response({'message': 'Logout successful'})
        
        # Clear all auth cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        response.delete_cookie('csrftoken')
        
        return response

class RefreshTokenView(APIView):
    """Refresh JWT tokens using the refresh token from cookies"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get refresh token from cookie
            refresh_token = request.COOKIES.get('refresh_token')
            
            if not refresh_token:
                logger.warning("Refresh token not found in cookies")
                return Response(
                    {'error': 'Refresh token not found'}, 
                    status=401
                )
            
            # Validate and refresh the token
            try:
                refresh = RefreshToken(refresh_token)
                # Get user from the refresh token
                user_id = refresh.payload.get('user_id')
                if not user_id:
                    raise TokenError("Invalid token payload")
                
                # Import User model here to avoid circular imports
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                
                # Create response with user data
                response = Response({
                    'message': 'Token refreshed successfully',
                    'user': UserSerializer(user).data
                })
                
                # Set new tokens in cookies
                return set_auth_cookies(response, user, request)
                
            except (TokenError, InvalidToken) as e:
                logger.warning(f"Invalid refresh token: {str(e)}")
                response = Response(
                    {'error': 'Invalid or expired refresh token'}, 
                    status=401
                )
                # Clear invalid cookies
                response.delete_cookie('access_token', path='/')
                response.delete_cookie('refresh_token', path='/')
                response.delete_cookie('csrftoken', path='/')
                return response
                
        except Exception as e:
            logger.error(f"Unexpected error in token refresh: {str(e)}")
            return Response(
                {'error': 'Token refresh failed'}, 
                status=500
            )
        
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user
 
    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user
    
    
    
    