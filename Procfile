release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
