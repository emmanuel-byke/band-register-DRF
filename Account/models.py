from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    username = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    fname = models.CharField(max_length=128, null=True, blank=True)
    lname = models.CharField(max_length=128, null=True, blank=True)
    gender = models.CharField(max_length=10, default='Male')
    occupation = models.CharField(max_length=128, default='Student')
    profile_picture = models.ImageField(upload_to='profile_pictures', null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    logged_in_times = models.PositiveIntegerField(default=0)

    divisions = models.ManyToManyField('Data.Division', blank=True, related_name='users')
    
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username
    
    