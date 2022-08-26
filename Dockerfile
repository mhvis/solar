FROM python:3.10

ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# The .dockerignore file only includes necessary files/folders
COPY . .
RUN pip install --no-cache-dir .
