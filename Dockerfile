# Note: issue with using Docker is that the UDP broadcasts are not forwarded to
# the host network by default, thus it requires some extra steps to get it to
# work.

FROM python:3.9-alpine

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/src/app

COPY . .

RUN pip install --no-cache-dir .

ENTRYPOINT [ "samil" ]
