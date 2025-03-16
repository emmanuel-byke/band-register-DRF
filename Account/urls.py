from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PublicUserViewSet, SignupView, LoginView, ManageUserView, LogoutView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'public-users', PublicUserViewSet, basename='public-user')

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/me/', ManageUserView.as_view(), name='current-user'),
    path('', include(router.urls)),
]