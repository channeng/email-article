# Pull base image.
FROM ubuntu

# Install Supervisor.
RUN \
  mkdir /var/log/flask && \
  mkdir /home/ubuntu && \
  mkdir /home/ubuntu/email-article && \
  apt-get update && \
  apt-get install -y supervisor python-pip wget vim git lsb-release curl python-dev libxml2-dev libxslt1-dev zlib1g-dev && \
  rm -rf /var/lib/apt/lists/* && \
  sed -i 's/^\(\[supervisord\]\)$/\1\nnodaemon=true/' /etc/supervisor/supervisord.conf

# expose port 5000 of the container (HTTP port, change to 443 for HTTPS)
EXPOSE 5000

# Create virtualenv.
RUN \
  pip install --upgrade pip && \
  pip install --upgrade virtualenv && \
  virtualenv -p /usr/bin/python2.7 /home/ubuntu/.virtualenvs/env

# Setup for ssh onto github, clone and define working directory
ADD credentials/ /home/ubuntu/.credentials/
RUN \
  chmod 600 /home/ubuntu/.credentials/repo-key && \
  echo "IdentityFile /home/ubuntu/.credentials/repo-key" >> /etc/ssh/ssh_config && \
  echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

RUN date > last_updated_7.txt
RUN git clone git@github.com:channeng/email-article.git /home/ubuntu/email-article

WORKDIR /home/ubuntu/email-article

# Install app requirements
RUN \
  . /home/ubuntu/.virtualenvs/env/bin/activate && \
  pip install https://s3-us-west-2.amazonaws.com/jdimatteo-personal-public-readaccess/nltk-2.0.5-https-distribute.tar.gz && \
  pip install -r requirements.txt

ADD config.py /home/ubuntu/email-article

ENV FLASK_APP=main.py

# Copy supervisor configs
RUN \
  cp configs/supervisord.conf /etc/supervisor/supervisord.conf && \
  cp configs/conf.d/*.conf /etc/supervisor/conf.d/
