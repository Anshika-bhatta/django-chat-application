from django.contrib import admin
from .models import ChatRoom, ChatMessage, UserProfile, Friendship

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['user', 'message', 'timestamp', 'edited', 'edited_at', 'deleted', 'file', 'file_type']
    can_delete = False

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'privacy', 'created_by', 'created_at', 'participant_count']
    list_filter = ['privacy', 'created_at']
    search_fields = ['name', 'created_by__username']
    inlines = [ChatMessageInline]
    filter_horizontal = ['participants']
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'short_message', 'timestamp', 'edited', 'deleted']
    list_filter = ['room', 'timestamp', 'user', 'edited', 'deleted']
    search_fields = ['user__username', 'message']
    readonly_fields = ['timestamp', 'edited_at']
    list_per_page = 50
    
    def short_message(self, obj):
        if obj.deleted:
            return "[DELETED]"
        return obj.message[:75] + '...' if len(obj.message) > 75 else obj.message
    short_message.short_description = 'Message'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'last_activity', 'is_online', 'friend_count', 'theme']
    list_filter = ['last_activity', 'theme']
    search_fields = ['user__username']
    
    def friend_count(self, obj):
        return len(obj.get_friends())
    friend_count.short_description = 'Friends'

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'created', 'accepted']
    list_filter = ['accepted', 'created']
    search_fields = ['from_user__username', 'to_user__username']