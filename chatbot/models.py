from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q  

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_activity = models.DateTimeField(default=timezone.now)
    friends = models.ManyToManyField(
        'self', 
        through='Friendship', 
        symmetrical=False, 
        related_name='related_to'
    )
    theme = models.CharField(max_length=10, default='light')
    
    def is_online(self):
        return (timezone.now() - self.last_activity).total_seconds() < 300
        
    def get_friends(self):
        accepted_friendships = Friendship.objects.filter(
            Q(from_user=self, accepted=True) | 
            Q(to_user=self, accepted=True)
        )
        friend_users = []
        for friendship in accepted_friendships:
            if friendship.from_user == self:
                friend_users.append(friendship.to_user.user)
            else:
                friend_users.append(friendship.from_user.user)
        return friend_users
    
    def get_friendships(self):
        return Friendship.objects.filter(
            Q(from_user=self) | 
            Q(to_user=self)
        )
    
    def add_friend(self, friend_profile):
        friendship, created = Friendship.objects.get_or_create(
            from_user=self,
            to_user=friend_profile
        )
        return friendship
    
    def remove_friend(self, friend_profile):
        Friendship.objects.filter(
            Q(from_user=self, to_user=friend_profile) |
            Q(from_user=friend_profile, to_user=self)
        ).delete()
        return True
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online() else 'Offline'}"

class Friendship(models.Model):
    from_user = models.ForeignKey(UserProfile, related_name='from_friends', on_delete=models.CASCADE)
    to_user = models.ForeignKey(UserProfile, related_name='to_friends', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
    
    def __str__(self):
        return f"{self.from_user.user.username} -> {self.to_user.user.username} ({'Accepted' if self.accepted else 'Pending'})"

class ChatRoom(models.Model):
    PRIVACY_CHOICES = [
        ('private', 'Private'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        default=1
    )
    created_at = models.DateTimeField(auto_now_add=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    
    def __str__(self):
        return f"{self.name} ({self.privacy})"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    file_type = models.CharField(max_length=20, null=True, blank=True)
    
    # Read receipts
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:20]}..."