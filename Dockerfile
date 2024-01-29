FROM python:3.12.1-slim-bullseye

WORKDIR /app
COPY ./requirements.txt /app
COPY ./*.py /app
RUN pip install -r requirements.txt

EXPOSE 101
ENV FLASK_APP=app.py
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]