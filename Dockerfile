FROM python:3-slim
ENV PIP_NO_CACHE_DIR=off
# Need to install pipenv from master until this is released
# https://github.com/pypa/pipenv/issues/4337
RUN apt-get update && apt-get install -y git
RUN pip install --no-cache-dir git+https://github.com/pypa/pipenv.git
WORKDIR /opt/fotrino/
COPY src/ ./
RUN apt-get install -y libpq-dev gcc
RUN pipenv install --system
RUN pip uninstall -y pipenv
RUN apt-get --purge remove -y git gcc
RUN apt-get autoremove -y
EXPOSE 65442
CMD gunicorn --config /opt/fotrino/gunicorn.conf.py wsgi:app
