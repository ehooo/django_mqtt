#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR/mosquitto-auth-plug
sudo mv auth-plug.so /etc/mosquitto/
cd ..
rm -fr mosquitto-auth-plug org.eclipse.mosquitto

sudo cp $DIR/auth_plugin.conf /etc/mosquitto/conf.d/auth_plugin.conf
