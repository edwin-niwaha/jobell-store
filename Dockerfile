FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DJANGO_ENV=production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements-production.txt ./
COPY vendor ./vendor
RUN sha256sum --check vendor/djoser.sha256 && python -m pip install --upgrade "pip==26.2.1" && python -m pip install -r requirements-production.txt
COPY manage.py gunicorn.conf.py ./
COPY core ./core
COPY apps ./apps
COPY api ./api
COPY services ./services
COPY repositories ./repositories
COPY scripts/check_production_branch.py ./scripts/check_production_branch.py
COPY templates ./templates
COPY static ./static
RUN python manage.py collectstatic --noinput --settings=core.settings.build
RUN useradd --create-home app && chown -R app:app /app
USER app
CMD ["gunicorn", "core.wsgi:application", "--config", "gunicorn.conf.py"]
