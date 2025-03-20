from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Q, Sum, F, ExpressionWrapper, DurationField
from django.db.models import Exists, OuterRef
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth

from rest_framework import viewsets, filters, status
from drf_nested_forms.parsers import NestedMultiPartParser
from .models import (
    Venue, SongsLearnt, Division, Attendance, Absent,
    Ratings, Performance, PendingRequest, PendingActivity, Feedback
)
from .serializers import (
    VenueSerializer, SongsLearntSerializer, DivisionListSerializer,
    DivisionDetailSerializer, AttendanceSerializer, AbsentSerializer, 
    RatingsSerializer, PerformanceSerializer, PendingRequestSerializer,
    PendingActivitySerializer, FeedbackSerializer
)

from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model


@require_GET
def csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})

class PendingActivityViewSet(viewsets.ModelViewSet):
    queryset = PendingActivity.objects.all()
    serializer_class = PendingActivitySerializer
    filter_backends = [filters.SearchFilter]
    filterset_fields = ['venue', 'showPoster']
    search_fields = ['title', 'desc']
    parser_classes = [NestedMultiPartParser]
    permission_classes = [AllowAny]

    def perform_destroy(self, instance):
        # Delete associated Venue when Activity is deleted
        if instance.venue:
            instance.venue.delete()
        super().perform_destroy(instance)
        
class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['date', 'place', 'role']
    search_fields = ['place', 'role', 'startTime', 'endTime', 'date', 'divisions__name']
    ordering_fields = ['date', 'startTime', 'place']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter for upcoming venues
        upcoming = self.request.query_params.get('upcoming')
        if upcoming and upcoming.lower() == 'true':
            queryset = queryset.filter(date__gte=timezone.now().date())
        
        # Filter by division
        division_id = self.request.query_params.get('division')
        if division_id:
            queryset = queryset.filter(divisions__id=division_id)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get venues scheduled in the next 30 days"""
        upcoming_venues = Venue.objects.filter(
            date__gte=timezone.now().date(),
            date__lte=timezone.now().date() + timedelta(days=30)
        ).order_by('date', 'startTime')
        
        serializer = self.get_serializer(upcoming_venues, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def divisions(self, request, pk=None):
        """Get all divisions associated with this venue"""
        venue = self.get_object()
        divisions = venue.divisions.all()
        serializer = DivisionListSerializer(divisions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_division(self, request):
        venues = Venue.objects.filter(divisions__isnull=False).distinct()
        venues = self.filter_queryset(venues)
        serializer = self.get_serializer(venues, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='upcoming-with-division')
    def upcoming_with_division(self, request):
        """Get upcoming venues (next 30 days) associated with divisions, filtered by users"""
        """GET venues/upcoming-with-division/?users=1,3&search=Training&ordering=-date"""
        """params: { users: selectedUsers, ordering: '-date' };"""
        
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        queryset = Venue.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            divisions__isnull=False
        )
        
        # Add user filter (from query param)
        user_ids = request.query_params.get('users')
        if user_ids:
            try:
                # Convert comma-separated string to list of integers
                user_ids = [int(id) for id in user_ids.split(',')]
                queryset = queryset.filter(divisions__users__id__in=user_ids)
            except ValueError:
                return Response(
                    {"error": "Invalid user ID format"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Apply distinct, filtering, and ordering
        queryset = queryset.distinct()
        queryset = self.filter_queryset(queryset)  # Applies search/ordering
        queryset = queryset.order_by('date', 'startTime')  # Default ordering
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
    
    
    
    
    
    

class TestConnection(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        return Response({'connected': True})
    
    
    
    
    






class SongsLearntViewSet(viewsets.ModelViewSet):
    queryset = SongsLearnt.objects.all()
    serializer_class = SongsLearntSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['date']
    search_fields = ['title']
    ordering_fields = ['date', 'title']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by division
        division_id = self.request.query_params.get('division')
        if division_id:
            queryset = queryset.filter(divisions__id=division_id)
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def divisions(self, request, pk=None):
        """Get all divisions that have learned this song"""
        song = self.get_object()
        divisions = song.divisions.all()
        serializer = DivisionListSerializer(divisions, many=True, context={'request': request})
        return Response(serializer.data)


class DivisionViewSet(viewsets.ModelViewSet):
    queryset = Division.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'role', 'isRegistered', 'is_active', 'showRatings', 'showVenue', 'showUser']
    search_fields = ['name', 'role', 'userRole', 'shortWords', 'title']
    ordering_fields = ['name', 'created_at']
    
    def get_serializer_class(self):
        # if self.action == 'list':
        #     return DivisionListSerializer
        return DivisionDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter active divisions
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)
            
        # Filter by venue
        venue_id = self.request.query_params.get('venue')
        if venue_id:
            queryset = queryset.filter(venues__id=venue_id)
            
        return queryset
    
    def filter_queryset(self, queryset):
        from Account.models import User
        
        queryset = super().filter_queryset(queryset)
        user = self.request.user
        
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_joined=Exists(
                    User.objects.filter(
                        id=user.id,
                        divisions=OuterRef('pk')
                    )
                )
            )
            # Get current ordering and prepend '-is_joined'
            current_order = list(queryset.query.order_by)
            new_order = ['is_joined']
            new_order.extend(current_order)
            queryset = queryset.order_by(*new_order)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def create_venue(self, request, pk=None):
        division = self.get_object()
        serializer = VenueSerializer(data=request.data)
        
        if serializer.is_valid():
            venue = serializer.save()
            PendingRequest.objects.create(
                venue=venue,
                division=division
            )
            return Response({'detail': 'Venue added successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_division(self, request, pk=None):
        """
        POST /divisions/{division_id}/remove_venue/
        Expects JSON: { "venue_id": <id> }
        """
        division = self.get_object()
        venue_id = request.data.get('venue_id')
        try:
            venue = Venue.objects.get(pk=venue_id)
            PendingRequest.objects.filter(division=division, venue=venue).delete()
            return Response({'detail': 'venue removed successfully.'}, status=status.HTTP_200_OK)
        except Venue.DoesNotExist:
            return Response({'detail': 'venue not found.'}, status=status.HTTP_404_NOT_FOUND)
    

    @action(detail=False, methods=['post'], url_path='users/(?P<user_id>[^/.]+)/all')
    def get_user_divisions_details(self, request, user_id=None):
        """Get divisions by user ID with date filtering"""
        from datetime import datetime
        
        User = get_user_model()
        target_user = get_object_or_404(User, id=user_id)
        
        divId = request.data.get('divId')
        user_divisions =  target_user.divisions.all() if divId=='all' else target_user.divisions.filter(id=divId)
        
        # Parse dates with validation
        try:
            start_date_str = request.data.get('startDate')
            end_date_str = request.data.get('endDate')
            
            startDate = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str \
                else date.today().replace(day=1)
            endDate = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str \
                else date.today()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, 
                        status=status.HTTP_400_BAD_REQUEST)

        # Common filter for all venue-related queries
        date_filter = {
            'venue__date__range': [startDate, endDate]
        }

        # Attendance calculations
        attendance_queryset = Attendance.objects.filter(
            division__in=user_divisions,
            **date_filter
        ).distinct()

        attendance_totals = attendance_queryset.aggregate(
            total_sessions=Sum('sessions'),
            total_attended=Sum('attendance')
        )

        # Absence calculations
        absent_queryset = Absent.objects.filter(
            division__in=user_divisions,
            **date_filter
        ).distinct()

        absent_totals = absent_queryset.aggregate(
            total_sessions=Sum('sessions'),
        )

        # Duration calculations
        absents = absent_queryset.annotate(
            duration=ExpressionWrapper(
                F('venue__endTime') - F('venue__startTime'),
                output_field=DurationField()
            )
        )

        attendances = attendance_queryset.annotate(
            duration=ExpressionWrapper(
                F('venue__endTime') - F('venue__startTime'),
                output_field=DurationField()
            )
        )

        # Statistics
        attendance_duration_data = attendances.aggregate(total_duration=Sum('duration'))
        absent_duration_data = absents.aggregate(total_duration=Sum('duration'))

        total_sessions = (attendance_totals['total_sessions'] or 0) + (absent_totals['total_sessions'] or 0)
        total_attended = attendance_totals['total_attended'] or 0

        stats = {
            'totalSessions': total_sessions,
            'attendedSessions': attendance_totals['total_attended'] or 0,
            'totalHours': ((attendance_duration_data['total_duration'] or timedelta(0)) + 
                           ((absent_duration_data['total_duration'] or timedelta(0)))).total_seconds(),
            'attendedHours': (attendance_duration_data['total_duration'] or timedelta(0)).total_seconds(),
            'attendancePercentage': (total_attended/total_sessions)*100 if total_sessions > 0 else 0,
        }

        serializers = {
            'attendances': AttendanceSerializer(attendances, many=True).data,
            'absents': AbsentSerializer(absents, many=True).data,
            'divisions': DivisionListSerializer(target_user.divisions.all(), many=True).data # This was supposed to be on it's own action
        }

        return Response({
            'stats': stats,
            'serializers': serializers,
            'date_range': {
                'start': startDate.isoformat(),
                'end': endDate.isoformat()
            }
        })
        
    @action(detail=False, methods=['post'])
    def get_all_users_divisions_details(self, request):
        """Get divisions by user ID with date filtering"""
        from datetime import datetime
        
        
        divId = request.data.get('divId')
        divisions = Division.objects.all() if divId=='all' or divId is None else Division.objects.filter(id=divId)
        
        # Parse dates with validation
        try:
            start_date_str = request.data.get('startDate')
            end_date_str = request.data.get('endDate')
            
            startDate = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str \
                else date.today().replace(day=1)
            endDate = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str \
                else date.today()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, 
                        status=status.HTTP_400_BAD_REQUEST)

        # Common filter for all venue-related queries
        date_filter = {
            'venue__date__range': [startDate, endDate]
        }
        
        
        # Attendance calculations
        attendance_queryset = Attendance.objects.filter(
            division__in=divisions
        ).distinct()

        attendance_totals = attendance_queryset.aggregate(
            total_sessions=Sum('sessions'),
            total_attended=Sum('attendance')
        )

        # Absence calculations
        absent_queryset = Absent.objects.filter(
            division__in=divisions
        ).distinct()

        absent_totals = absent_queryset.aggregate(
            total_sessions=Sum('sessions'),
        )


        total_sessions = (attendance_totals['total_sessions'] or 0) + (absent_totals['total_sessions'] or 0)
        total_attended = attendance_totals['total_attended'] or 0

        stats = {
            'totalSessions': total_sessions,
            'attendedSessions': attendance_totals['total_attended'] or 0,
            'attendancePercentage': (total_attended/total_sessions)*100 if total_sessions > 0 else 0,
            'top_absence_reason': absent_queryset.values('reason').annotate(value=Count('reason')).order_by('-value').first()
        }


        serializers = {
            'attendances': AttendanceSerializer(attendance_queryset, many=True).data,
            'absents': AbsentSerializer(absent_queryset, many=True).data,
            'divisions': DivisionListSerializer(divisions, many=True).data,
        }

        return Response({
            'stats': stats,
            'serializers': serializers,
            'date_range': {
                'start': startDate.isoformat(),
                'end': endDate.isoformat()
            }
        })
        
    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)/venues')
    def user_venues(self, request, user_id=None):
        """Get venues by user ID with association check"""
        # 1. Get target user from URL parameter
        User = get_user_model()
        target_user = get_object_or_404(User, id=user_id)
        
        # 2. Get user's divisions
        user_divisions = target_user.divisions.all()
        
        # 3. Filter venues based on user's divisions and their own pending requests
        now = timezone.now()
        current_date = now.date()
        current_time = now.time()
        venue_groups = {
            'new': Venue.objects.filter(
                pending_requests__division__in=user_divisions,
                pending_requests__pending=False,
                pending_requests__admin_check=False,
                pending_requests__admin_accept=False
            ).filter(
                Q(date__lt=current_date) | 
                Q(date=current_date, startTime__lt=current_time)
            ).distinct(),
            'pending': Venue.objects.filter(
                pending_requests__division__in=user_divisions,
                pending_requests__user=target_user,
                pending_requests__pending=True,
                pending_requests__admin_check=False,
                pending_requests__admin_accept=False
            ).distinct(),
            'accepted': Venue.objects.filter(
                pending_requests__division__in=user_divisions,
                pending_requests__user=target_user,
                pending_requests__pending=False,
                pending_requests__admin_check=True,
                pending_requests__admin_accept=True
            ).distinct(),
            'rejected': Venue.objects.filter(
                pending_requests__division__in=user_divisions,
                pending_requests__user=target_user,
                pending_requests__pending=True,
                pending_requests__admin_check=True,
                pending_requests__admin_accept=False
            ).distinct(),
        }

        # 4. Serialize with target user in context
        serialized = {
            key: VenueSerializer(
                value, 
                many=True, 
                context={
                    'request': request,
                    'target_user': target_user  # Pass user to serializer
                }
            ).data
            for key, value in venue_groups.items()
        }
        
        return Response(serialized)
    
    @action(detail=True, methods=['post'])
    def process_venue_response(self, request, pk=None):
        """Approve a venue request"""
        division = self.get_object()
        reason = request.data.get('reason', 'Work/Study')
        username = request.data.get('username')
        req_admin_review = request.data.get('req_admin_review', True)
        req_admin_accept = request.data.get('req_admin_accept', False)
        is_user_state = request.data.get('is_user_state', True)
        venue_id = request.data.get('id')
        venue = Venue.objects.get(id=venue_id)
        try:
            request_obj = PendingRequest.objects.get(
                division=division,
                venue=venue
            )
            if(is_user_state):
                try:
                    request_obj.user = get_user_model().objects.get(username=username)
                except: 
                    pass
                if(not req_admin_review):
                    request_obj.reason = reason
                    request_obj.attended = False
                    Absent.objects.create(
                        venue=venue,
                        division=division, 
                        reason=reason
                    )
                request_obj.admin_check = not req_admin_review
                request_obj.admin_accept = not req_admin_review
                request_obj.pending = req_admin_review
            else:
                if(req_admin_accept):
                    request_obj.attended = True
                    Attendance.objects.create(
                        venue=venue,
                        division=division,
                        sessions=2,
                        attendance=2,
                    )
                request_obj.pending = not req_admin_accept
                request_obj.admin_check = True
                request_obj.admin_accept = req_admin_accept
                              
            request_obj.save()
            
            return Response({'detail': 'Venue request approved.'}, status=status.HTTP_200_OK)
        except PendingRequest.DoesNotExist:
            return Response({'detail': 'Pending request not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    
    @action(detail=True, methods=['get'])
    def get_users(self, request, pk=None):
        """Get all users for this division"""
        from Account.serializers import UserSerializer
        
        division = self.get_object()
        users = division.users.all()
        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def songs(self, request, pk=None):
        """Get all songs learned by this division"""
        division = self.get_object()
        songs = division.songs.all()
        serializer = SongsLearntSerializer(songs, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def attendance_stats(self, request, pk=None):
        """Get attendance statistics for this division"""
        division = self.get_object()
        attendance_data = division.attendance.all()
        
        total_sessions = sum(data.sessions for data in attendance_data)
        total_attendance = sum(data.attendance for data in attendance_data)
        
        attendance_rate = (total_attendance / total_sessions * 100) if total_sessions else 0
        
        return Response({
            'total_sessions': total_sessions,
            'total_attendance': total_attendance,
            'attendance_rate': round(attendance_rate, 2)
        })
    
    @action(detail=True, methods=['get'])
    def ratings_stats(self, request, pk=None):
        """Get rating statistics for this division"""
        division = self.get_object()
        ratings = division.ratings.all()
        
        if not ratings:
            return Response({
                'average': 0,
                'count': 0,
                'distribution': {
                    '1': 0, '2': 0, '3': 0, '4': 0, '5': 0
                }
            })
        
        avg_rating = ratings.aggregate(avg=Avg('value'))['avg']
        distribution = {
            '1': ratings.filter(value__lt=2).count(),
            '2': ratings.filter(value__gte=2, value__lt=3).count(),
            '3': ratings.filter(value__gte=3, value__lt=4).count(),
            '4': ratings.filter(value__gte=4, value__lt=5).count(),
            '5': ratings.filter(value__gte=5).count(),
        }
        
        return Response({
            'average': round(avg_rating, 2) if avg_rating else 0,
            'count': ratings.count(),
            'distribution': distribution
        })


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venue', 'division']
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple attendance records at once"""
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=['post'])
    def monthly_attendance(self, request):
        total_months = int(request.data.get('totalMonths', 3))
        today = timezone.now().date()
        start_date = today - relativedelta(months=total_months)

        # Generate list of month starts
        months = []
        current = start_date.replace(day=1)
        while current <= today:
            months.append(current)
            current += relativedelta(months=1)

        # Query and process data
        divisions = Division.objects.all()
        aggregated = (
            self.get_queryset()
            .filter(venue__date__gte=start_date)
            .annotate(month=TruncMonth('venue__date'))
            .values('month', 'division__name')
            .annotate(total_attended=Sum('attendance'))
        )

        # Create lookup dictionary
        attendance_map = {
            (entry['month'].strftime('%Y-%m'), entry['division__name']): 
            entry['total_attended'] for entry in aggregated
        }

        # Build result structure
        result = []
        for month in months:
            item = {}
            item['month'] = month.strftime("%B")
            for div in divisions:
                item[div.name] = attendance_map.get((month.strftime('%Y-%m'), div.name), 0)
            result.append(item)
            
        
        return Response(result)


class AbsentViewSet(viewsets.ModelViewSet):
    queryset = Absent.objects.all()
    serializer_class = AbsentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['venue', 'division', 'reason']
    search_fields = ['reason']


class RatingsViewSet(viewsets.ModelViewSet):
    queryset = Ratings.objects.all()
    serializer_class = RatingsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'division']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get ratings for current user
        if self.request.user.is_authenticated:
            my_ratings = self.request.query_params.get('my_ratings')
            if my_ratings and my_ratings.lower() == 'true':
                queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        # Automatically set user to current user if not specified
        user = serializer.validated_data.get('user')
        if not user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.all()
    serializer_class = PerformanceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['division', 'venue']


class PendingRequestViewSet(viewsets.ModelViewSet):
    queryset = PendingRequest.objects.all()
    serializer_class = PendingRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'venue', 'attended', 'pending']
    search_fields = ['reason', 'user__fname', 'user__lname', 'division__name', 'division__role']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Division managers can see all requests for their divisions
        if self.request.user.is_authenticated and hasattr(self.request.user, 'is_division_manager') and self.request.user.is_division_manager:
            # Implement logic to filter for divisions managed by this user
            pass
        # Regular users can only see their own requests
        elif self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    
    def perform_create(self, serializer):
        # Automatically set user to current user if not specified
        user = serializer.validated_data.get('user')
        if not user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
            
    @action(detail=False, methods=['get'])
    def venues(self, request):
        """Get all pending venue requests available for all users in all divisions"""
        pending_req = PendingRequest.objects.filter(user__isnull=False).filter(
            Q(
                pending=True,
                admin_check=False
            )
        ).distinct()
        pending_req = self.filter_queryset(pending_req)
        return Response(self.get_serializer(pending_req, many=True).data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending request"""
        pending_request = self.get_object()
        
        # Check if user has permission to approve
        if not (hasattr(request.user, 'is_division_manager') and request.user.is_division_manager):
            return Response(
                {"detail": "You do not have permission to approve requests."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        pending_request.accepted = True
        pending_request.pending = False
        pending_request.save()
        
        # If this was an attendance request, create an attendance record
        if pending_request.attended and pending_request.divId and pending_request.venue:
            # Logic to update attendance records
            pass
            
        serializer = self.get_serializer(pending_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending request"""
        pending_request = self.get_object()
        
        # Check if user has permission to reject
        if not (hasattr(request.user, 'is_division_manager') and request.user.is_division_manager):
            return Response(
                {"detail": "You do not have permission to reject requests."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        pending_request.accepted = False
        pending_request.pending = False
        pending_request.save()
            
        serializer = self.get_serializer(pending_request)
        return Response(serializer.data)





class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all().order_by('-created_at')
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'sender', 'completed']
    search_fields = ['title', 'highlitedTitle', 'desc', 'user__fname', 'user__lname']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Division managers can see all feedback
        if self.request.user.is_authenticated and self.request.user.is_admin:
            return queryset
        # Regular users can only see their own feedback
        elif self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    