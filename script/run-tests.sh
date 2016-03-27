#!/usr/bin/env bash
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata initial_data
python manage.py test
