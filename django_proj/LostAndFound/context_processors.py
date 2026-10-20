# LostAndFound/context_processors.py
from django.conf import settings

def express_settings(request):
    return {
        'EXPRESS_URL': getattr(settings, 'EXPRESS_URL', 'http://localhost:3000')
    }