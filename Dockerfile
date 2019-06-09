# Pull base image.
FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y software-properties-common vim build-essential && \
    add-apt-repository ppa:jonathonf/python-3.6

RUN apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3-pip python3.6-venv && \
    apt-get install -y git tmux

# update pip
RUN python3.6 -m pip install pip --upgrade && \
        python3.6 -m pip install wheel

# Install Supervisor.
RUN \
  mkdir /var/log/flask && \
  mkdir /home/ubuntu && \
  mkdir /home/ubuntu/email-article && \
  apt-get update && \
  apt-get install -y supervisor wget vim git lsb-release curl libxml2-dev libxslt1-dev zlib1g-dev sqlite3 libsqlite3-dev sqlite3 && \
  rm -rf /var/lib/apt/lists/* && \
  sed -i 's/^\(\[supervisord\]\)$/\1\nnodaemon=true/' /etc/supervisor/supervisord.conf

# expose port 5000 of the container (HTTP port, change to 443 for HTTPS)
EXPOSE 5000

# Create virtualenv.
RUN \
  python3.6 -m pip install --upgrade pip && \
  python3.6 -m pip install --upgrade virtualenv && \
  virtualenv -p /usr/bin/python3.6 /home/ubuntu/.virtualenvs/env

# Setup for ssh onto github, clone and define working directory
ADD credentials/ /home/ubuntu/.credentials/
RUN \
  chmod 600 /home/ubuntu/.credentials/repo-key && \
  echo "IdentityFile /home/ubuntu/.credentials/repo-key" >> /etc/ssh/ssh_config && \
  echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

RUN date > last_updated_8.txt
RUN git clone git@github.com:channeng/email-article.git /home/ubuntu/email-article

WORKDIR /home/ubuntu/email-article

# Install app requirements
RUN \
  . /home/ubuntu/.virtualenvs/env/bin/activate && \
  python3.6 -m pip install -r requirements.txt

ADD config.py /home/ubuntu/email-article

ENV FLASK_APP=main.py

# Copy supervisor configs
RUN \
  cp configs/supervisord.conf /etc/supervisor/supervisord.conf && \
  cp configs/conf.d/*.conf /etc/supervisor/conf.d/
