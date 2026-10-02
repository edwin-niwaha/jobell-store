web: gunicorn core.wsgi:application --config gunicorn.conf.py
worker: celery -A core worker --loglevel=INFO --concurrency=2
