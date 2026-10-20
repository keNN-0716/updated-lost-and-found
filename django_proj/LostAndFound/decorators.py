from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def management_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is staff or has the 'Management' role
        if request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'role', None) == 'Management'):
            return view_func(request, *args, **kwargs)
        
        # If they are logged in but NOT management, send them to their home page
        if request.user.is_authenticated:
            messages.error(request, "You do not have permission to access the management area.")
            return redirect('user_home_page')
            
        # If they aren't logged in at all, send them to login
        return redirect('login')
        
    return _wrapped_view