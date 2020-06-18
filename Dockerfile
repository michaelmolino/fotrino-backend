FROM python:3
RUN pip install git+https://github.com/pypa/pipenv.git
WORKDIR /opt/fotrino/
COPY src/ ./
RUN pipenv install --system
EXPOSE 65442
CMD gunicorn --config /opt/fotrino/gunicorn.conf.py wsgi:app
