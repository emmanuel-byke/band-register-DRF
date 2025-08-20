from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.validators import UniqueValidator

User = get_user_model()

class UserSerializer(serializers.ModelSerializer): 
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'username', 'profile_picture', 'gender', 'occupation', 'is_admin', 'fname', 
                  'lname', 'divisions', 'is_active', 'logged_in_times')
        
    
    

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=4)
    username = serializers.CharField(required=True)
    divisions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'password', 'phone_number', 'profile_picture', 'gender', 'occupation', 'fname', 
                  'lname', 'divisions', 'is_active', 'is_admin', 'logged_in_times')
        extra_kwargs = {
            'username': {
                'validators': [
                    UniqueValidator(
                        queryset=User.objects.all(),
                        message="A user with that username already exists."
                    )
                ],
                'error_messages': {
                    'required': 'Username is required.'
                }
            },
            'password': {'write_only': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'gender': {'required': False, 'allow_blank': True},
            'occupation': {'required': False, 'allow_blank': True},
            'fname': {'required': False, 'allow_blank': True},
            'lname': {'required': False, 'allow_blank': True},
            'profile_picture': {'required': False},
            'is_active': {'required': False},
            'is_admin': {'required': False},
            'divisions': {'required': False},
        }

    def create(self, validated_data):
        divisions = validated_data.pop('divisions', [])
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            phone_number=validated_data['phone_number'],
            gender=validated_data.get('gender', 'Male'),
            occupation=validated_data.get('occupation', 'Student'),
            fname=validated_data.get('fname'),
            lname=validated_data.get('lname'),
            # profile_picture=validated_data.get('profile_picture'),
        )
        if divisions:
            user.divisions.set(divisions)
        return user
        
    def get_divisions(self, obj):
        """Safely handle divisions for different user types"""
        if not isinstance(obj, User) or obj.is_anonymous:
            return []
            
        from Data.serializers import DivisionDetailSerializer
        return DivisionDetailSerializer(
            obj.divisions.all(),
            many=True,
            context=self.context
        ).data
    
    
    
class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'fname', 'lname', 'divisions', 'is_admin', 'is_active', 'profile_picture')
        read_only_fields = ('username', 'fname', 'lname', 'divisions')
   
   
        
class AuthTokenSerializer(serializers.Serializer):
    """Serializer for the user authentication token"""
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, attrs):
        """Validate and authenticate the user"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            msg = 'Unable to authenticate with provided credentials'
            raise serializers.ValidationError(msg, code='authentication')
        
        attrs['user'] = user
        return attrs
    
    
            
        
        
        
        