.HELP: shell  ## Django shell
shell:
	python manage.py shell

.HELP: migrate  ## Migrate DB to current models
migrate:
	python manage.py makemigrations
	python manage.py migrate

.HELP: run  ## Run local server
run:
	python manage.py runserver

.HELP: help  ## Display this message
help:
	@grep -E \
		'^.HELP: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".HELP: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
