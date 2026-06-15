def karams_globals(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'user_is_admin': request.user.is_admin,
        'user_tema': request.user.tema,
    }
