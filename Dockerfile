FROM python:3.13

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8888

RUN mkdir static
RUN chmod 755 static

CMD ["sh", "-c", "\
    python manage.py migrate && \
    python manage.py shell < create_superuser.py && \
    python manage.py collectstatic && \
    gunicorn --workers 3 --bind 0.0.0.0:8888 backend.wsgi:application \
"]