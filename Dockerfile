# Pull base image.
FROM python:3.7-buster
LABEL maintainer="Shannon Chan <channeng@hotmail.com>"

RUN apt-get update||exit 0
RUN apt-get install python3-pip vim sudo dbus curl bc supervisor -y

# Install Supervisor.
RUN \
  mkdir /var/log/flask && \
  mkdir /home/ubuntu && \
  mkdir /home/ubuntu/email-article && \
  apt-get update && \
  apt-get install -y lsb-release curl libxml2-dev libxslt1-dev zlib1g-dev sqlite3 libsqlite3-dev sqlite3 && \
  rm -rf /var/lib/apt/lists/* && \
  sed -i 's/^\(\[supervisord\]\)$/\1\nnodaemon=true/' /etc/supervisor/supervisord.conf

# expose port 5000 of the container (HTTP port, change to 443 for HTTPS)
EXPOSE 5000

# Create virtualenv.
RUN \
  pip install --upgrade pip && \
  pip install --upgrade virtualenv && \
  virtualenv -p /usr/local/bin/python /home/ubuntu/.virtualenvs/env

# Setup for ssh onto github, clone and define working directory
ADD credentials/ /home/ubuntu/.credentials/
RUN \
  chmod 600 /home/ubuntu/.credentials/repo-key && \
  echo "IdentityFile /home/ubuntu/.credentials/repo-key" >> /etc/ssh/ssh_config && \
  echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

RUN date > last_updated_2.txt
RUN git clone git@github.com:channeng/email-article.git /home/ubuntu/email-article

WORKDIR /home/ubuntu/email-article

# Install app requirements
RUN \
  . /home/ubuntu/.virtualenvs/env/bin/activate && \
  pip install -r requirements.txt

ADD config.py /home/ubuntu/email-article

ENV FLASK_APP=main.py

# Fix errors on flask db cli
# http://click.palletsprojects.com/en/5.x/python3/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Copy supervisor configs
RUN \
  cp configs/supervisord.conf /etc/supervisor/supervisord.conf && \
  cp configs/conf.d/*.conf /etc/supervisor/conf.d/
