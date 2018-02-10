# Keyword Spam classifier

A Docker implementation of keyword spam classifier running on Flask, managed with supervisord.

## How does it work?

See JIRA documentation here: https://carousell.atlassian.net/wiki/spaces/SEARCH/pages/41576506/Search+exp+-+Keyword+Spam


# Getting Started

## Running this setup

1. From server, run the following command:
	```bash
	cd ~ && mkdir credentials
	```

2. From local project dir, copy dockerfile, credentials and docker install script into server
	```bash
	scp Dockerfile $SERVER:/home/<user>/
	scp credentials/* $SERVER:/home/<user>/credentials
	scp scripts/debian_jessy_docker_setup.sh $SERVER:/home/<user>/
	```

3. Install Docker
	```bash
	sudo bash scripts/debian_jessy_docker_setup.sh
	```

4. Build docker image
	```bash
	docker build -t kw-spam .
	```
	(Optional) Stop any containers running on existing docker image
	```bash
	docker stop $(docker ps -f ancestor=kw-spam --format "{{.ID}}")
	```
5. Run docker container
	```bash
	docker run -p 3020:3020 -d kw-spam /usr/bin/supervisord --nodaemon
	```

6. Enter bash terminal
	```bash
	sudo docker exec -it $(sudo docker ps -f ancestor=data-workflows --format "{{.ID}}") /bin/bash
	```
