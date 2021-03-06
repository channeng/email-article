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
	- To obtain SuperUser access for Docker command, run: `sudo usermod -aG docker $USER`
	- Exit server and ssh back in

4. (Optional) Stop any containers running on existing docker image
	```bash
	docker container stop email-article
	```

5. Build docker image
	```bash
	docker build -t email-article .
	```

	Note: If memory error on installing lxml, run the following and try building docker image again.
	```bash
	sudo dd if=/dev/zero of=/swapfile bs=1024 count=524288
	sudo chmod 600 /swapfile
	sudo mkswap /swapfile
	sudo swapon /swapfile
	docker build -t email-article .
	```

	after you're done: 
	```bash
	sudo swapoff /swapfile
	```

7. Run docker container
	```bash
	# To mount docker volume using local dir
	# Changes will be reflected on local dir db
	docker run -d --name email-article -p 80:5000 -v /path/to/database:/home/ubuntu/email-article/database -v /path/to/ticker_plots:/home/ubuntu/email-article/app/static/ticker_plots email-article /usr/bin/supervisord --nodaemon
	```
	(Optional, if running with Docker volume)
	```bash
	# Create docker volume for database
	docker volume create email-article-db
	# Check that volume exists:
	docker volume ls | grep email-article-db
	# Run container with docker volume
	docker run -v email-article-db:/home/ubuntu/email-article/database -p 80:5000 -d email-article /usr/bin/supervisord --nodaemon
	```

8. Enter bash terminal
	```bash
	docker exec -it email-article /bin/bash
	```

## Other commands:
- To save a backup of the database:
	```bash
	docker cp email-article:/home/ubuntu/email-article/database/ database_copy/app.db
	```

- To copy an updated config into Docker container:
	```bash
	docker cp email-article/config.py email-article:/home/ubuntu/email-article
	```

- To test DB migration:
	- Copy database/app.db from docker -> server -> database/app.db
	- Run the following commands:
		```bash
		rm -rf migrations/

		# Delete any previous alembic version in DB
		sqlite3 database/app.db < delete_alembic_version.sqlite

		# Create migrations folder to prepare for migration script
		flask db init

		# Generate migration script
		flask db migrate

		# Check that changes are as expected, before executing the following:
		flask db upgrade
		```