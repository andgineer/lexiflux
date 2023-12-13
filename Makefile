.HELP: shell  ## Django shell
shell:
	python manage.py shell

.HELP: migrate  ## Migrate DB to current models
migrate:
	python manage.py makemigrations
	python manage.py makemigrations core
	python manage.py migrate

.HELP: pages  ## Create random book with random pages
pages:
	python manage.py add-pages

.HELP: init-db  ## KILL Database and reinit new one
init-db: kill-db migrate admin pages

.HELP: kill-db  ## KILL Database
kill-db:
	rm -f db.sqlite3

.HELP: admin  ## Create admin
admin:
	DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser --username admin --email admin@example.com --noinput

.HELP: run  ## Run local server
run:
	python manage.py runserver

.HELP: reqs  ## Upgrade requirements including pre-commit
reqs:
	pre-commit autoupdate
	bash ./scripts/compile_requirements.sh
	pip install -r requirements.dev.txt
	pip install -r requirements.txt

.HELP: sql  ## sqlite3
sql:
	sqlite3 db.sqlite3 -header

.HELP: get-books  ## Select books from DB
get-books:
	sqlite3 db.sqlite3 "SELECT * FROM lexiflux_book;"

.HELP: js  ## Bundle and minify JavaScript in Django static folder
js:
	npm run build

.HELP: help  ## Display this message
help:
	@grep -E \
		'^.HELP: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".HELP: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
