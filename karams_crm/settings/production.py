import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = env.bool('DEBUG', default=False)


def _normalize_allowed_hosts(hosts):
    """Converte entradas comuns do Railway/README para formato Django."""
    normalized = []
    for host in hosts:
        host = (host or '').strip()
        if not host:
            continue
        if host.startswith('https://'):
            host = host[8:]
        elif host.startswith('http://'):
            host = host[7:]
        host = host.split('/')[0].rstrip('/')
        if host.startswith('*.'):
            host = host[1:]
        if host == '*':
            normalized.append('.railway.app')
            continue
        normalized.append(host)
    return list(dict.fromkeys(normalized))


def _host_allowed_by_list(host, allowed_hosts):
    if host in allowed_hosts:
        return True
    return any(
        pattern.startswith('.') and host.endswith(pattern)
        for pattern in allowed_hosts
        if pattern.startswith('.')
    )


def _build_csrf_trusted_origins(allowed_hosts, railway_domain, extra_csrf_hosts=()):
    """
    Django NÃO aceita wildcard em CSRF_TRUSTED_ORIGINS (ex: https://*.railway.app).
    Monta a lista com domínios explícitos.
    """
    origins = []
    for item in env.list('CSRF_TRUSTED_ORIGINS', default=[]):
        item = (item or '').strip()
        if not item or '*' in item:
            continue
        if not item.startswith('http'):
            item = f'https://{item}'
        origins.append(item.rstrip('/'))

    if railway_domain:
        origins.append(f'https://{railway_domain}'.rstrip('/'))

    for host in allowed_hosts:
        if host.startswith('.'):
            continue
        if host in ('localhost', '127.0.0.1'):
            origins.append(f'http://{host}')
        else:
            origins.append(f'https://{host}')

    for host in extra_csrf_hosts:
        host = (host or '').strip()
        if not host or host.startswith('.'):
            continue
        if _host_allowed_by_list(host, allowed_hosts):
            origins.append(f'https://{host}')

    return list(dict.fromkeys(origins))


ALLOWED_HOSTS = _normalize_allowed_hosts(
    env.list(
        'ALLOWED_HOSTS',
        default=['.railway.app', 'crm-karams.up.railway.app', 'localhost', '127.0.0.1'],
    ),
)

RAILWAY_DOMAIN = (os.environ.get('RAILWAY_PUBLIC_DOMAIN') or '').strip()
if RAILWAY_DOMAIN and RAILWAY_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)

for extra in _normalize_allowed_hosts(env.list('EXTRA_ALLOWED_HOSTS', default=[])):
    if extra not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(extra)

# Domínio público do CRM — incluído no CSRF quando ALLOWED_HOSTS usa só wildcard (.railway.app).
PRODUCTION_PUBLIC_HOSTS = _normalize_allowed_hosts(
    env.list('PRODUCTION_PUBLIC_HOSTS', default=['crm-karams.up.railway.app']),
)

CSRF_TRUSTED_ORIGINS = _build_csrf_trusted_origins(
    ALLOWED_HOSTS,
    RAILWAY_DOMAIN,
    extra_csrf_hosts=PRODUCTION_PUBLIC_HOSTS,
)

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
