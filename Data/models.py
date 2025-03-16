from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class Venue(models.Model): 
    date = models.DateField()
    startTime = models.TimeField()
    endTime = models.TimeField(null=True, blank=True)
    place = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(max_length=100, null=True, blank=True)
    img = models.FileField(upload_to='venue_img', null=True, blank=True)
    
    class Meta:
        ordering = ['-date', 'startTime']
        indexes = [ models.Index(fields=['-date', 'place']), models.Index(fields=['role']), ]
    def __str__(self):
        return self.place or ""

class SongsLearnt(models.Model):
    title = models.CharField(max_length=128)
    date = models.DateField()
    
    class Meta:
        indexes = [models.Index(fields=['date', 'title'])]
        ordering = ['date', 'title']
    def __str__(self):
        return self.title

class Division(models.Model):
    name = models.CharField(max_length=128)
    role = models.CharField(max_length=128)
    userRole = models.CharField(max_length=128, default='Member')
    isRegistered= models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    value = models.ImageField(upload_to='divisions', null=True, blank=True)
    showRatings = models.BooleanField(default=True)    
    shortWords = models.CharField(max_length=1024, null=True, blank=True)
    showVenue = models.BooleanField(default=True)
    title = models.CharField(max_length=1024, null=True, blank=True)
    titleDesc = models.TextField(null=True, blank=True)
    titleQuote = models.CharField(max_length=1024, null=True, blank=True)
    showUser = models.BooleanField(default=True)
    baseUser = models.CharField(max_length=128, default='Member')
    baseUserModifier = models.CharField(max_length=128, default='Available')
    
    venues = models.ManyToManyField(Venue, through='PendingRequest', blank=True, related_name='divisions')
    songs = models.ManyToManyField(SongsLearnt, blank=True, related_name='divisions')
    attendances = models.ManyToManyField(Venue, through='Attendance', related_name='division_attendees')
    absents = models.ManyToManyField(Venue, through='Absent', related_name='division_absentee')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [ models.Index(fields=['name']) ]
        ordering = ['created_at']
        unique_together = ['name', 'role']
        
    def __str__(self):
        return self.name or ""
    
class Attendance(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='attendances')
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='attendance')
    sessions = models.IntegerField(default=1)
    attendance = models.IntegerField(default=0)
    
    def __str__(self):
        return f'{self.division.name} {self.venue.date}' or ""    
    
class Absent(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='absent')
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='absent')
    sessions = models.IntegerField(default=1)
    attendance = models.IntegerField(default=0) #so that the data can be combined with Attendance model data
    reason = models.CharField(default='study/work', max_length=128)
    
    def __str__(self):
        return self.reason
    
class Ratings(models.Model):
    user = models.OneToOneField('Account.User', on_delete=models.SET_NULL, related_name='ratings', null=True, blank=True)
    value = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='ratings', null=True, blank=True)
    
class Performance(models.Model):
    venue = models.ManyToManyField(Venue)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='performance', null=True, blank=True)    
    
class PendingRequest(models.Model):
    user = models.ForeignKey('Account.User', related_name='pending_requests', on_delete=models.SET_NULL, null=True, blank=True )
    venue = models.ForeignKey(Venue, related_name='pending_requests', on_delete=models.SET_NULL, null=True, blank=True )
    division = models.ForeignKey(Division, related_name='pending_requests', on_delete=models.SET_NULL, null=True, blank=True )
    reason = models.CharField(max_length=128, null=True, blank=True)
    
    pending = models.BooleanField(default=False) # the venue is ready to be processed by user
    admin_check = models.BooleanField(default=False) # admin/system has reviewed the request
    admin_accept = models.BooleanField(default=False) # admin/system thinks you're saying the truth
    attended = models.BooleanField(default=False) # approved that you were present or not
    
    def __str__(self):
        return self.attended    
    
class PendingActivity(models.Model):
    title = models.CharField(max_length=256)
    desc = models.CharField(max_length=1024, null=True, blank=True)
    venue = models.OneToOneField(
        Venue,
        on_delete=models.CASCADE,
        related_name='pending_activity',
        null=True, 
        blank=True,
    )
    showPoster = models.BooleanField(default=True)
    poster = models.FileField(upload_to='pending_activity')
    
    def __str__(self):
        return self.title or ""

class Feedback(models.Model):
    user = models.ForeignKey('Account.User', related_name='feedbacks', on_delete=models.CASCADE)
    sender = models.ForeignKey('Account.User', related_name='sent_feedbacks', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=256)
    highlighted_title = models.CharField(max_length=128)
    desc = models.TextField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} - {self.user.fname}'
    
    
    
    
    
    