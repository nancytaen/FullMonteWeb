web: gunicorn fullMonteWeb.wsgi --timeout 3600
release: python manage.py makemigrations && python manage.py migrate --fake
