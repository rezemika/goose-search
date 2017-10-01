install-back:
	pip3 install --upgrade -r requirements.txt

collectstatic:
	python3 manage.py collectstatic

migrate:
	python3 manage.py migrate

load-factory-data:
	python3 manage.py load_factory_data

new-secret-key:
	python3 manage.py new_secret_key

reset-db:
	python3 manage.py flush

run-back:
	python3 manage.py runserver 0.0.0.0:8000

test:
	python3 manage.py test search

help:
	@echo "install-back: updates the current virtualenv with the content of 'requirements.txt'"
	@echo "collectstatic: collects the staticfiles for the admin pages"
	@echo "migrate: migrates the database"
	@echo "load-factory-data: loads data in DB to allow rapid testing"
	@echo "new-secret-key: generates a new SECRET_KEY"
	@echo "reset-db: resets the database"
	@echo "run-back: runs the development server on port 8000"
	@echo "test: runs the unit tests"
