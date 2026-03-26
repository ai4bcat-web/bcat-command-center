web: gunicorn wsgi:app -c gunicorn.conf.py
release: flask db upgrade && flask create-admin
