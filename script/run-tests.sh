#!/usr/bin/env bash
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata initial_data
python manage.py test
coverage run --source='.' manage.py test
coverage report -m --skip-covered
coverage html
