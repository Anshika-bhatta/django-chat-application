from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q
import json
import os
from datetime import datetime

from .models import ChatRoom, ChatMessage, UserProfile, Friendship

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('chat')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    return render(request, 'chatbot/register.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def chat_view(request, room_name=None):
    # Update user's last activity
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.last_activity = timezone.now()
    profile.save()
    
    # Get user's friends and pending requests
    user_profile = UserProfile.objects.get(user=request.user)
    friends = user_profile.get_friends()
    pending_requests = Friendship.objects.filter(to_user=user_profile, accepted=False)
    
    # Get private chat rooms for the user with other participants pre-calculated
    user_rooms_with_participants = []
    for room in ChatRoom.objects.filter(participants=request.user, privacy='private'):
        other_participant = room.participants.exclude(id=request.user.id).first()
        user_rooms_with_participants.append({
            'room': room,
            'other_participant': other_participant
        })
    
    # If no room specified, show the first private chat or empty state
    if not room_name and user_rooms_with_participants:
        return redirect('chat_room', room_name=user_rooms_with_participants[0]['room'].name)
    
    # Initialize these variables to handle the case where there is no room
    room = None
    messages_list = []
    other_participant = None 
    
    if room_name:
        room = get_object_or_404(ChatRoom, name=room_name)
        if request.user not in room.participants.all():
            messages.error(request, "You don't have access to this chat room.")
            return redirect('chat')
        
        # Get last 50 messages
        messages_list = ChatMessage.objects.filter(room=room, deleted=False).order_by('-timestamp')[:50]
        # Get the other participant for the current room
        other_participant = room.participants.exclude(id=request.user.id).first() 
    
    # Get online users (those active in last 5 minutes)
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    online_profiles = UserProfile.objects.filter(last_activity__gte=five_minutes_ago).exclude(user=request.user)
    online_users = [profile.user for profile in online_profiles]
    
    # Get all users except current user for adding friends
    all_users = User.objects.exclude(id=request.user.id)
    
    return render(request, 'chatbot/chat.html', {
        'messages': reversed(messages_list),
        'room': room,
        'online_users': online_users,
        'friends': friends,
        'pending_requests': pending_requests,
        'user_rooms_with_participants': user_rooms_with_participants,
        'all_users': all_users,
        'user_theme': profile.theme,
        'other_participant': other_participant,
        'current_room_name': room_name
    })

@login_required
def add_friend(request, username):
    if request.method == 'POST':
        friend_user = get_object_or_404(User, username=username)
        user_profile = UserProfile.objects.get(user=request.user)
        friend_profile = UserProfile.objects.get(user=friend_user)
        
        # Check if friendship already exists in either direction
        existing_friendship = Friendship.objects.filter(
            (Q(from_user=user_profile, to_user=friend_profile) |
             Q(from_user=friend_profile, to_user=user_profile))
        ).first()
        
        if existing_friendship:
            if existing_friendship.accepted:
                return JsonResponse({'status': 'info', 'message': f"You are already friends with {username}."})
            else:
                if existing_friendship.from_user == user_profile:
                    return JsonResponse({'status': 'info', 'message': f"Friend request already sent to {username}."})
                else:
                    return JsonResponse({'status': 'info', 'message': f"You have a pending friend request from {username}."})
        else:
            friendship = user_profile.add_friend(friend_profile)
            return JsonResponse({'status': 'success', 'message': f"Friend request sent to {username}."})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def accept_friend(request, friendship_id):
    if request.method == 'POST':
        friendship = get_object_or_404(Friendship, id=friendship_id, to_user__user=request.user)
        friendship.accepted = True
        friendship.save()
        
        # Create a private chat room for the new friends
        room_name = f"private_{min(friendship.from_user.user.id, friendship.to_user.user.id)}_{max(friendship.from_user.user.id, friendship.to_user.user.id)}"
        room, created = ChatRoom.objects.get_or_create(
            name=room_name,
            privacy='private',
            defaults={'created_by': request.user}
        )
        
        if created:
            room.participants.add(friendship.from_user.user, friendship.to_user.user)
        
        return JsonResponse({'status': 'success', 'message': 'Friend request accepted!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def reject_friend(request, friendship_id):
    if request.method == 'POST':
        friendship = get_object_or_404(Friendship, id=friendship_id, to_user__user=request.user)
        friendship.delete()
        return JsonResponse({'status': 'success', 'message': 'Friend request rejected.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def create_private_chat(request, username):
    if request.method == 'POST':
        friend_user = get_object_or_404(User, username=username)
        user_profile = UserProfile.objects.get(user=request.user)
        friend_profile = UserProfile.objects.get(user=friend_user)
        
        # Check if they are friends
        friendship = Friendship.objects.filter(
            (Q(from_user=user_profile, to_user=friend_profile) |
             Q(from_user=friend_profile, to_user=user_profile)),
            accepted=True
        ).first()
        
        if friendship:
            room_name = f"private_{min(request.user.id, friend_user.id)}_{max(request.user.id, friend_user.id)}"
            room, created = ChatRoom.objects.get_or_create(
                name=room_name,
                privacy='private',
                defaults={'created_by': request.user}
            )
            
            if created:
                room.participants.add(request.user, friend_user)
            
            return JsonResponse({'status': 'success', 'room_name': room_name})
        else:
            return JsonResponse({'status': 'error', 'message': 'You can only chat with friends.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def get_messages(request, room_name):
    room = get_object_or_404(ChatRoom, name=room_name)
    
    if request.user not in room.participants.all():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    messages_list = ChatMessage.objects.filter(room=room, deleted=False).order_by('timestamp')
    
    # Mark messages as read by current user
    unread_messages = messages_list.exclude(read_by=request.user)
    for msg in unread_messages:
        msg.read_by.add(request.user)
    
    messages_data = []
    for msg in messages_list:
        messages_data.append({
            'id': msg.id,
            'user': msg.user.username,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%H:%M:%S'),
            'is_current_user': msg.user == request.user,
            'edited': msg.edited,
            'edited_at': msg.edited_at.strftime('%H:%M:%S') if msg.edited_at else None,
            'file_url': msg.file.url if msg.file else None,
            'file_type': msg.file_type,
            'read_by': list(msg.read_by.values_list('username', flat=True))
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
def get_online_users(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.last_activity = timezone.now()
    profile.save()
    
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    online_profiles = UserProfile.objects.filter(last_activity__gte=five_minutes_ago).exclude(user=request.user)
    users_data = [{'username': profile.user.username, 'is_online': True} for profile in online_profiles]
    return JsonResponse({'online_users': users_data})

@login_required
def send_message(request, room_name):
    if request.method == 'POST':
        try:
            room = get_object_or_404(ChatRoom, name=room_name)
            
            if request.user not in room.participants.all():
                return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
            
            # Handle both form data and JSON data
            if request.FILES:
                # Form data with file upload
                message_text = request.POST.get('message', '').strip()
                file = request.FILES.get('file', None)
            else:
                # JSON data (text only)
                data = json.loads(request.body)
                message_text = data.get('message', '').strip()
                file = None
            
            file_type = None
            if file:
                # Validate file type and size
                if file.size > 10 * 1024 * 1024:  # 10MB limit
                    return JsonResponse({'status': 'error', 'message': 'File too large'})
                
                if file.content_type.startswith('image/'):
                    file_type = 'image'
                elif file.content_type.startswith('video/'):
                    file_type = 'video'
                elif file.content_type.startswith('audio/'):
                    file_type = 'audio'
                else:
                    file_type = 'document'
            
            if message_text or file:
                chat_message = ChatMessage.objects.create(
                    room=room,
                    user=request.user,
                    message=message_text,
                    file=file,
                    file_type=file_type
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': chat_message.id,
                        'user': request.user.username,
                        'message': message_text,
                        'timestamp': chat_message.timestamp.strftime('%H:%M:%S'),
                        'is_current_user': True,
                        'file_url': chat_message.file.url if chat_message.file else None,
                        'file_type': chat_message.file_type
                    }
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Empty message'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def edit_message(request, message_id):
    if request.method == 'POST':
        try:
            message = get_object_or_404(ChatMessage, id=message_id, user=request.user)
            data = json.loads(request.body)
            new_message = data.get('message', '').strip()
            
            if new_message:
                message.message = new_message
                message.edited = True
                message.edited_at = timezone.now()
                message.save()
                
                return JsonResponse({'status': 'success', 'message': 'Message updated successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Empty message'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def delete_message(request, message_id):
    if request.method == 'POST':
        try:
            message = get_object_or_404(ChatMessage, id=message_id, user=request.user)
            message.deleted = True
            message.save()
            
            return JsonResponse({'status': 'success', 'message': 'Message deleted successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def toggle_theme(request):
    if request.method == 'POST':
        try:
            profile = UserProfile.objects.get(user=request.user)
            profile.theme = 'dark' if profile.theme == 'light' else 'light'
            profile.save()
            
            return JsonResponse({'status': 'success', 'theme': profile.theme, 'message': f'Themed changed to {profile.theme} mode'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def typing_indicator(request, room_name):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            is_typing = data.get('is_typing', False)
            
            return JsonResponse({'status': 'success', 'is_typing': is_typing})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def remove_friend(request, username):
    if request.method == 'POST':
        try:
            friend_user = get_object_or_404(User, username=username)
            user_profile = UserProfile.objects.get(user=request.user)
            friend_profile = UserProfile.objects.get(user=friend_user)
            
            user_profile.remove_friend(friend_profile)
            
            # Also delete the private chat room
            room_name = f"private_{min(request.user.id, friend_user.id)}_{max(request.user.id, friend_user.id)}"
            ChatRoom.objects.filter(name=room_name).delete()
            
            return JsonResponse({'status': 'success', 'message': f'Removed {username} from friends'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def search_users(request):
    try:
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'users': []})
        
        # Exclude current user and existing friends
        user_profile = UserProfile.objects.get(user=request.user)
        friends = user_profile.get_friends()  
        
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)
        
        users_data = []
        for user in users:
            # Check if already friends
            is_friend = user in friends
            if not is_friend:  # Only show non-friends in search
                users_data.append({
                    'username': user.username,
                    'is_online': user.userprofile.is_online
                })
        
        return JsonResponse({'users': users_data})
    except Exception as e:
        return JsonResponse({'users': [], 'error': str(e)})