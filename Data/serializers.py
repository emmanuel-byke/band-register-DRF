from rest_framework import serializers
from django.db.models import Avg, Count
from rest_framework.validators import UniqueTogetherValidator
from django.utils import timezone
from .models import (
    Venue, SongsLearnt, Division, Attendance, Absent,
    Ratings, Performance, PendingRequest, PendingActivity, Feedback
)
from django.contrib.auth import get_user_model

        
class VenueSerializer(serializers.ModelSerializer):
    # division_count = serializers.SerializerMethodField()
    # attendance_rate = serializers.SerializerMethodField()
    divisions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    is_user_associated = serializers.SerializerMethodField()
    
    class Meta:
        model = Venue
        fields = '__all__'
        extra_fields = ['divisions', 'is_user_associated']
        extra_kwargs = {
            'endTime': {'required': False, 'allow_null': True},
            'place': {'required': False, 'allow_blank': True},
            'role': {'required': False, 'allow_blank': True},
            'img': {'required': False}
        }
        
    def get_is_user_associated(self, obj):
        #user = self.context['request'].user #for authenticated user
        target_user = self.context.get('target_user') #get user id from endpoint url
        return obj.divisions.filter(users=target_user).exists()
    
    
    # def get_division_count(self, obj):
    #     return obj.divisions.count()
    
    # def get_attendance_rate(self, obj):
    #     attendance_count = obj.attendances.aggregate(
    #         total_attendance=Count('attendance')
    #     ).get('total_attendance', 0)
        
    #     if not attendance_count:
    #         return 0
        
    #     total_sessions = obj.attendances.aggregate(
    #         total_sessions=Count('sessions')
    #     ).get('total_sessions', 0)
        
    #     return attendance_count / total_sessions if total_sessions else 0
        
        
class PendingActivitySerializer(serializers.ModelSerializer):
    venue = VenueSerializer()
    venue_detail = serializers.SerializerMethodField()

    class Meta:
        model = PendingActivity
        fields = '__all__'
        extra_fields = ['venue_detail']

    def create(self, validated_data):
        venue_data = validated_data.pop('venue')
        venue = Venue.objects.create(**venue_data)
        activity = PendingActivity.objects.create(venue=venue, **validated_data)
        return activity

    def update(self, instance, validated_data):
        venue_data = validated_data.pop('venue', None)
        if venue_data:
            venue_instance = instance.venue
            for attr, value in venue_data.items():
                setattr(venue_instance, attr, value)
            venue_instance.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def get_venue_detail(self, obj):
        if obj.venue:
            return {
                'date': obj.venue.date,
                'place': obj.venue.place,
                'startTime': obj.venue.startTime,
                'endTime': obj.venue.endTime,
            }
        return None
    
        
        
        
        
        
        
        
        
    





class SongsLearntSerializer(serializers.ModelSerializer):
    division_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SongsLearnt
        fields = '__all__'
        extra_fields = ['division_count']
    
    def get_division_count(self, obj):
        return obj.divisions.count()


class AttendanceSerializer(serializers.ModelSerializer):
    venue_detail = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = ['id', 'venue', 'division', 'sessions', 'attendance', 'venue_detail', 'attendance_rate']
    
    def get_venue_detail(self, obj):
        return {
            'date': obj.venue.date,
            'place': obj.venue.place,
            'startTime': obj.venue.startTime,
            'endTime': obj.venue.endTime,
            'role': obj.venue.role,
        }
    
    def get_attendance_rate(self, obj):
        return (obj.attendance / obj.sessions) * 100 if obj.sessions else 0


class AbsentSerializer(serializers.ModelSerializer):
    venue_detail = serializers.SerializerMethodField()
    division_name = serializers.ReadOnlyField(source='division.name')
    
    class Meta:
        model = Absent
        extra_fields = ['venue_detail', 'division_name']
        fields = '__all__'
    
    def get_venue_detail(self, obj):
        return {
            'date': obj.venue.date,
            'place': obj.venue.place,
            'startTime': obj.venue.startTime,
            'endTime': obj.venue.endTime,
        }



class RatingsSerializer(serializers.ModelSerializer):
    from Account.serializers import UserSerializer
    
    user_detail = UserSerializer(source='user', read_only=True)
    division_name = serializers.ReadOnlyField(source='division.name')
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Ratings
        fields = ['id', 'user', 'value', 'division', 'created_at', 
                 'updated_at', 'user_detail', 'division_name', 'is_owner']
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'value': {'min_value': 1.0, 'max_value': 5.0}
        }

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.user

    def create(self, validated_data):
        user = self.context['request'].user
        division = validated_data['division']
        
        # Update existing rating or create new
        rating, created = Ratings.objects.update_or_create(
            user=user,
            division=division,
            defaults={'value': validated_data['value']}
        )
        return rating



class PerformanceSerializer(serializers.ModelSerializer):
    venues = VenueSerializer(source='venue', many=True, read_only=True)
    division_name = serializers.ReadOnlyField(source='division.name')
    venue_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Performance
        fields = ['id', 'venue', 'division', 'venues', 'division_name', 'venue_count']
    
    def get_venue_count(self, obj):
        return obj.venue.count()

    
class PendingRequestSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    division_detail = serializers.SerializerMethodField()
    venue_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PendingRequest
        extra_fields = ['user']
        fields = '__all__'
        
    def get_user_detail(self, obj):
        if obj.user:
            return {
                'firstname': obj.user.fname,  # adjust the attribute name as defined in your User model
                'lastname': obj.user.lname,
                'username': obj.user.username,
            }
        return None

    def get_division_detail(self, obj):
        if obj.division:
            return {
                'name': obj.division.name,
                'role': obj.division.role,
            }
        return None

    def get_venue_detail(self, obj):
        if obj.venue:
            return {
                'date': obj.venue.date,
                'place': obj.venue.place,
                'startTime': obj.venue.startTime,
                'endTime': obj.venue.endTime,
            }
        return None



class FeedbackSerializer(serializers.ModelSerializer):
    from Account.serializers import PublicUserSerializer
    
    user_detail = PublicUserSerializer(source='user', read_only=True)
    sender_detail = PublicUserSerializer(source='sender', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'user', 'user_detail', 'sender', 'sender_detail', 'title', 'shown_count',
            'highlighted_title', 'desc', 'completed', 'created_at', 'created_at_formatted'
        ]
        read_only_fields = ['created_at', 'shown_count']
        extra_kwargs = {
            'user': {'required': True},
            'sender': {'required': False}
        }

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def validate(self, data):
        # Automatically set sender to current user if not provided
        if 'sender' not in data:
            data['sender'] = self.context['request'].user
        
        # Validate sender permissions
        request_user = self.context['request'].user
        if data['sender'] != request_user and not request_user.is_admin:
            raise serializers.ValidationError(
                {"sender": "You can only set yourself as the sender unless you're an admin."}
            )
        
        return data


class DivisionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing divisions"""
    venue_count = serializers.SerializerMethodField()
    songs_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Division
        fields = [
            'id', 'name', 'role', 'userRole', 'isRegistered', 
            'is_active', 'value', 'venue_count', 'songs_count', 'average_rating'
        ]
        
    def create(self, validated_data):
        venue_data = validated_data.pop('venue')
        venue = Venue.objects.create(**venue_data)
        activity = Division.objects.create(**validated_data)
        activity.venues.add(venue)
        return activity

    def update(self, instance, validated_data):
        venue_data = validated_data.pop('venue', None)
        if venue_data:
            venue_instance = instance.venue
            for attr, value in venue_data.items():
                setattr(venue_instance, attr, value)
            venue_instance.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def get_venue_count(self, obj):
        return obj.venues.count()
    
    def get_songs_count(self, obj):
        return obj.songs.count()
    
    def get_average_rating(self, obj):
        avg = obj.ratings.aggregate(avg_value=Avg('value')).get('avg_value')
        return round(avg, 2) if avg else 0
    
    


class DivisionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single division view"""
    venue_data = VenueSerializer(source='venues', many=True, read_only=True)
    songs = SongsLearntSerializer(many=True, read_only=True)
    attendance_data = AttendanceSerializer(source='attendance', many=True, read_only=True)
    absent_data = AbsentSerializer(source='absent', many=True, read_only=True)
    ratings_data = RatingsSerializer(source='ratings', many=True, read_only=True)
    performance_data = PerformanceSerializer(source='performance', many=True, read_only=True)
    pending_requests_data = PendingRequestSerializer(source='pending_requests', many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    venue_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Division
        fields = '__all__'
        extra_fields = [
            'attendance_data', 'absent_data', 'ratings_data', 
            'performance_data', 'pending_requests_data', 'average_rating',
            'venue_stats'
        ]
    
    def get_average_rating(self, obj):
        avg = obj.ratings.aggregate(avg_value=Avg('value')).get('avg_value')
        return round(avg, 2) if avg else 0
    
    def get_venue_stats(self, obj):
        today = timezone.now().date()  # Get the current date
        total_venues = obj.venues.count()
        upcoming_venues = obj.venues.filter(date__gte=today).count()
        
        return {
            'total': total_venues,
            'upcoming': upcoming_venues,
            'past': total_venues - upcoming_venues
        }
    
    def create(self, validated_data):
        division = Division.objects.create(**validated_data)
        return division

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
        
        
        
        