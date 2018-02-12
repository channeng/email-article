# News Article to Email application

Article-to-email takes a url link to any news article and sends the contents of the article to a given email in plain text.

It is useful in cases where the recipient would like to forward relevant articles to themselves but only has access to email content.

## How does it work?

This is a Docker implementation of article-to-email application running on Flask, managed with supervisord. 

Given a link to the article and the email of the recipient, the app will scrape the contents of the article, pass the contents to an email server in plain text and dispatch the email to the given recipient email address.

# Getting Started

## Running this setup

1. From server, run the following command:
	```bash
	cd ~
	git clone git@github.com:channeng/email-article.git
	cd email-article
	```

2. From local, copy credentials and config into server
	```bash
	scp -r credentials $SERVER:/home/ubuntu/email-article/credentials
	scp config.py $SERVER:/home/ubuntu/email-article/
	```

3. In server, install Docker and build docker image
	```bash
	sudo bash scripts/debian_jessy_docker_setup.sh
	```

4. Build docker image
	```bash
	sudo docker build -t email-article .
	```
	(Optional) Stop any containers running on existing docker image
	```bash
	sudo docker stop $(sudo docker ps -f ancestor=email-article --format "{{.ID}}")
	```

5. Run docker container
	```bash
	sudo docker run -p 5000:5000 -d email-article /usr/bin/supervisord --nodaemon
	```

	Note: If memory error on installing lxml, run the following and try building docker image again.
	```bash
	sudo dd if=/dev/zero of=/swapfile bs=1024 count=524288
	sudo chmod 600 /swapfile
	sudo mkswap /swapfile
	sudo swapon /swapfile
	sudo docker run -p 5000:5000 -d email-article /usr/bin/supervisord --nodaemon
	```

	after you're done: 
	```bash
	sudo swapoff /swapfile
	```

6. Enter bash terminal
	```bash
	sudo docker exec -it $(sudo docker ps -f ancestor=email-article --format "{{.ID}}") /bin/bash
	```
