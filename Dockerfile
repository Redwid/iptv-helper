FROM python:3.12.1-slim-bullseye

WORKDIR /app
COPY ./requirements.txt /app/
COPY ./*.py /app/
RUN pip install -r requirements.txt

EXPOSE 101
CMD [ "python3", "-m" , "app"]