release: python manage.py migrate && python manage.py preparar_senha_admin && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
