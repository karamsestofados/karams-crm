import threading

_local = threading.local()


def get_current_user():
    return getattr(_local, 'user', None)


def set_current_user(user):
    _local.user = user


def clear_current_user():
    if hasattr(_local, 'user'):
        del _local.user


def set_audit_fields(instance, user, is_create=False):
    if not user or not user.is_authenticated:
        return
    if is_create or not instance.pk:
        instance.created_by = user
    instance.updated_by = user
