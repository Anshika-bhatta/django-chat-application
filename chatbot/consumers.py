import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, UserProfile, ChatMessage
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Check if user is authenticated
        if self.scope['user'].is_anonymous:
            await self.close()
            return
        
        # Verify user has access to this room
        if await self.has_access():
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Update user's last activity
            await self.update_user_activity()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'typing':
                # Broadcast typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_message',
                        'username': self.scope['user'].username,
                        'is_typing': text_data_json.get('is_typing', False)
                    }
                )
            elif message_type == 'chat_message':
                # Save and broadcast the message
                message = text_data_json.get('message', '').strip()
                if message:
                    saved_message = await self.save_message(message)
                    
                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': saved_message['message'],
                            'username': self.scope['user'].username,
                            'timestamp': saved_message['timestamp'],
                            'message_id': saved_message['id']
                        }
                    )
        except json.JSONDecodeError:
            # Invalid JSON, ignore
            pass
        except Exception as e:
            # Log error but don't crash
            print(f"Error in receive: {e}")

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))
        
    async def typing_message(self, event):
        # Don't send typing indicator to the sender
        if event['username'] != self.scope['user'].username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def has_access(self):
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            return self.scope['user'] in room.participants.all()
        except ChatRoom.DoesNotExist:
            return False
        except Exception:
            return False
        
    @database_sync_to_async
    def save_message(self, message_text):
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            message = ChatMessage.objects.create(
                room=room,
                user=self.scope['user'],
                message=message_text
            )
            return {
                'id': message.id,
                'message': message.message,
                'timestamp': message.timestamp.strftime('%H:%M:%S')
            }
        except Exception as e:
            print(f"Error saving message: {e}")
            return {
                'id': None,
                'message': message_text,
                'timestamp': timezone.now().strftime('%H:%M:%S')
            }
        
    @database_sync_to_async
    def update_user_activity(self):
        try:
            profile, created = UserProfile.objects.get_or_create(user=self.scope['user'])
            profile.last_activity = timezone.now()
            profile.save()
        except Exception as e:
            print(f"Error updating user activity: {e}")
            pass