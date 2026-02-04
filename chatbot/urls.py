from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('room/<str:room_name>/', views.chat_view, name='chat_room'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='chatbot/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('api/messages/<str:room_name>/', views.get_messages, name='get_messages'),
    path('api/send-message/<str:room_name>/', views.send_message, name='send_message'),
    path('api/online-users/', views.get_online_users, name='get_online_users'),
    path('add-friend/<str:username>/', views.add_friend, name='add_friend'),
    path('accept-friend/<int:friendship_id>/', views.accept_friend, name='accept_friend'),
    path('reject-friend/<int:friendship_id>/', views.reject_friend, name='reject_friend'),
    path('remove-friend/<str:username>/', views.remove_friend, name='remove_friend'),
    path('create-private-chat/<str:username>/', views.create_private_chat, name='create_private_chat'),
    path('api/edit-message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('api/delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('api/toggle-theme/', views.toggle_theme, name='toggle_theme'),
    path('api/typing/<str:room_name>/', views.typing_indicator, name='typing_indicator'),
    path('api/search-users/', views.search_users, name='search_users'),
    path('test-static/', views.test_static, name='test_static'), 
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)