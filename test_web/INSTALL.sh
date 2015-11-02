#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Install Python Enviroment"
sudo apt-get install python-virtualenv python-dev git -y -qq

echo "Install Mosquitto auth-plugin"
bash script/install_mosquitto_auth_plugin.sh

echo "Install WebServer"
sudo apt-get install nginx supervisor gunicorn -y -qq

echo "Install Database"
sudo apt-get install libpq-dev postgresql postgresql-contrib

echo "Install dependencies"
virtualenv env
env/bin/pip install pip --upgrade
env/bin/pip install -r test_web/requirements.txt
env/bin/pip install -r requirements.txt

echo "
DJANGO_SETTINGS_MODULE=test_web.settings
DJANGO_WSGI_MODULE=test_web.wsgi
" >> env/bin/activate

echo "Configure supervisor"
echo "
[program:django_mqtt]
command = $PWD/env/bin/gunicorn test_web.wsgi:application -b 127.0.0.1:8000
directory = $PWD/
user = www-data
autostart = true
autorestart = true
# environment = DJANGO_SETTINGS_MODULE=\"test_web.settings\",DJANGO_WSGI_MODULE=\"test_web.wsgi\"
" > supervisor.conf
sudo cp supervisor.conf /etc/supervisor/conf.d/django_mqtt.conf
rm supervisor.conf

echo "Making directories"
mkdir private
chown www-data private
env/bin/python manage.py collectstatic

echo "Configure nginx"
echo "server {
    server_name _;

    access_log off;

    location /static/ {
        alias $PWD/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}" > nginx.conf
sudo cp nginx.conf /etc/nginx/sites-available/django_mqtt
sudo ln -s /etc/nginx/sites-available/django_mqtt /etc/nginx/sites-enabled/django_mqtt
sudo rm /etc/nginx/sites-enabled/default
rm nginx.conf

sudo service supervisor restart
sudo service nginx restart

echo "Configure Database"
sudo su postgres sh -c "createuser django_mqtt -P -d"
# sudo runuser -u postgres psql
env/bin/python manage.py syncdb
