from .models import Friendship

def unread_counts(request):
    if request.user.is_authenticated:
        try:
            user_profile = request.user.userprofile
            pending_requests_count = Friendship.objects.filter(
                to_user=user_profile, 
                accepted=False
            ).count()
            return {'pending_requests_count': pending_requests_count}
        except:
            return {'pending_requests_count': 0}
    return {'pending_requests_count': 0}