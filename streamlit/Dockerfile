FROM python:3.9.5-slim-buster

EXPOSE 8501

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install --upgrade pystan
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED "1"

COPY . /usr/src/app