.HELP: shell  ## Django shell
shell:
	python manage.py shell

.HELP: migrate  ## Migrate DB to current models
migrate:
	python manage.py makemigrations
	python manage.py migrate

.HELP: add-pages  ## Add pages to DB
add-pages:
	python manage.py add-pages

.HELP: init-db  ## Create tables and add pages to DB
init-db: migrate add-pages

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
	sqlite3 db.sqlite3

.HELP: get-books  ## Select books from DB
get-books:
	sqlite3 db.sqlite3 "SELECT * FROM lexiflux_book;"

.HELP: help  ## Display this message
help:
	@grep -E \
		'^.HELP: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".HELP: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
