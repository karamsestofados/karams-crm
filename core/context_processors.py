def karams_globals(request):
    if not request.user.is_authenticated:
        return {}
    pending_calendar_url = request.session.pop('pending_calendar_url', None)
    return {
        'user_is_admin': request.user.is_admin,
        'user_tema': request.user.tema,
        'pending_calendar_url': pending_calendar_url,
    }
