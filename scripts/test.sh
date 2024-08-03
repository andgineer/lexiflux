#!/usr/bin/env bash
#
# Run tests with generating Allure report
# To filter by test name use test.sh -k <test name>
# To filter by test marks use test.sh -m "mark1 and mark2"
# The report will be available at http://localhost:8800

python -m pytest --alluredir=allure-results tests $@
docker compose run --rm -it \
    allure \
    allure generate /allure-results -o /allure-report --clean

docker compose restart allure

echo "The report is on http://localhost:8800/"
