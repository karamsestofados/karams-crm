from core.novidades import SESSION_KEY, get_novidades


def karams_globals(request):
    if not request.user.is_authenticated:
        return {}
    pending_calendar_url = request.session.pop('pending_calendar_url', None)
    ctx = {
        'user_is_admin': request.user.is_admin,
        'user_tema': request.user.tema,
        'pending_calendar_url': pending_calendar_url,
    }
    if request.session.get(SESSION_KEY):
        ctx['mostrar_novidades'] = True
        ctx['novidades'] = get_novidades()
    return ctx
