from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated, AllowAny
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

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    
    @action(detail=False, methods=['post'])
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
    
@method_decorator(csrf_exempt, name='dispatch')
class SignupView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
        except IntegrityError as e:
            # Handle potential race condition errors
            error_messages = {
                'username': 'A user with that username already exists.',
                # 'email': 'This email address is already registered.'
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
        
        # Create token for the new user
        user = serializer.instance
        token, created = Token.objects.get_or_create(user=user)
        
        # Set token expiry
        token.created = timezone.now()
        token.save()
        
        # Login user (create session)
        login(request, user)
        
        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(ObtainAuthToken):
    """Custom login view to return auth token and user info"""
    serializer_class = AuthTokenSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # If token exists but is expired, create a new one
        if not created:
            token_expired_time = token.created + timedelta(seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS)
            if token_expired_time < timezone.now():
                token.delete()
                token = Token.objects.create(user=user)
        
        # Update token created time
        token.created = timezone.now()
        token.save()
        
        # Login user (create session)
        login(request, user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """Logout view to remove token and session"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Delete token
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass
        
        # Logout (delete session)
        logout(request)
        
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user
    
    
    
    