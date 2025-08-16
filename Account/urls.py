from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (UserViewSet, PublicUserViewSet, SignupView, LoginView, ManageUserView, LogoutView, 
    RefreshTokenView, get_csrf_token)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'public-users', PublicUserViewSet, basename='public-user')

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/me/', ManageUserView.as_view(), name='current-user'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('csrf-token/', get_csrf_token, name='csrf-token'),
    path('', include(router.urls)),
]