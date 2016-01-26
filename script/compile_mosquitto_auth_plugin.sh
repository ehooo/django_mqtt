#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sudo apt-get install mosquitto libssl-dev libmosquitto-dev libcurl4-openssl-dev -y

git clone http://git.eclipse.org/gitroot/mosquitto/org.eclipse.mosquitto.git
git clone https://github.com/jpmens/mosquitto-auth-plug.git

cp $DIR/config.mk mosquitto-auth-plug/config.mk
cd mosquitto-auth-plug
make
