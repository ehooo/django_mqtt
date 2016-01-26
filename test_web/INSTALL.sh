#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Install Python Enviroment"
sudo apt-get install python-virtualenv python-dev git -y -qq

echo "Install Mosquitto auth-plugin"
bash script/install_mosquitto_auth_plugin.sh

echo "Install WebServer"
sudo apt-get install nginx supervisor gunicorn -y -qq

echo "Install Database"
sudo apt-get install libpq-dev postgresql postgresql-contrib -y -qq
