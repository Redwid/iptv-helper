FROM python:3.12.1-slim-bullseye

WORKDIR /app
COPY ./requirements.txt /app/
COPY ./cache/xmltv.dtd /app/cache
COPY ./*.py /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    mkdir -p /log

EXPOSE 101
CMD [ "python3", "-m" , "app"]