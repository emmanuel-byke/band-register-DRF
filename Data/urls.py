from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import csrf_token_view
from .views import (
    VenueViewSet, SongsLearntViewSet, DivisionViewSet,
    AttendanceViewSet, AbsentViewSet, RatingsViewSet,
    PerformanceViewSet, PendingRequestViewSet,
    PendingActivityViewSet, FeedbackViewSet
)

router = DefaultRouter()
router.register(r'activities', PendingActivityViewSet, basename='activity')
router.register(r'venues', VenueViewSet, basename='venue')
router.register(r'songs', SongsLearntViewSet, basename='song')
router.register(r'divisions', DivisionViewSet, basename='division')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'absents', AbsentViewSet, basename='absent')
router.register(r'ratings', RatingsViewSet, basename='rating')
router.register(r'performances', PerformanceViewSet, basename='performance')
router.register(r'pending-requests', PendingRequestViewSet, basename='pending-request')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')


urlpatterns = [
    path("csrftoken/", csrf_token_view, name="csrftoken"),
    path('', include(router.urls)),
    # [GET /activities/ - List all activities, POST /activities/ - Create new actiity, GET /activities/1/ - Retrieve single actiity
    # PUT /activities/1/ - Update actiity, DELETE /activities/1/ - Delete actiity, GET /activities/?search=term - Search activities]
]




# division_venues = DivisionViewSet.as_view({
#     'get': 'venues',
# })

# division_songs = DivisionViewSet.as_view({
#     'get': 'songs',
# })

# division_attendance = DivisionViewSet.as_view({
#     'get': 'attendance_stats',
# })

# division_ratings = DivisionViewSet.as_view({
#     'get': 'ratings_stats',
# })

# venue_divisions = VenueViewSet.as_view({
#     'get': 'divisions',
# })

# song_divisions = SongsLearntViewSet.as_view({
#     'get': 'divisions',
# })

# # Add to urlpatterns
# urlpatterns += [
#     path('divisions/<int:pk>/venues/', division_venues, name='division-venues'),
#     path('divisions/<int:pk>/songs/', division_songs, name='division-songs'),
#     path('divisions/<int:pk>/attendance-stats/', division_attendance, name='division-attendance-stats'),
#     path('divisions/<int:pk>/ratings-stats/', division_ratings, name='division-ratings-stats'),
#     path('venues/<int:pk>/divisions/', venue_divisions, name='venue-divisions'),
#     path('songs/<int:pk>/divisions/', song_divisions, name='song-divisions'),
    
#     # Bulk operations
#     path('attendances/bulk/', AttendanceViewSet.as_view({'post': 'bulk_create'}), name='attendance-bulk-create'),
    
#     # Request approval/rejection
#     path('pending-requests/<int:pk>/approve/', 
#          PendingRequestViewSet.as_view({'post': 'approve'}), 
#          name='pending-request-approve'),
#     path('pending-requests/<int:pk>/reject/', 
#          PendingRequestViewSet.as_view({'post': 'reject'}), 
#          name='pending-request-reject'),
# ]