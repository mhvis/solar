FROM python:3.10

# I add Tini for better init management.
# See https://github.com/krallin/tini
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The .dockerignore file only includes necessary files/folders
COPY . .
RUN pip install --no-cache-dir .

ENTRYPOINT ["/tini", "--", "/usr/local/bin/samil"]
