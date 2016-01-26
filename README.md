Django-MQTT [![Build Status](https://travis-ci.org/ehooo/django_mqtt.svg?branch=master)](https://travis-ci.org/ehooo/django_mqtt)
===========
It is a django module that allow send your information stored in your database to MQTT server as MQTT Publisher.


Install
=======
Edit ```settings.py``` and add:
```
INSTALLED_APPS = (
  ...
  'django.contrib.admin',
  'django.contrib.auth',
  ...
  'django_mqtt.mosquitto.auth_plugin',
  'django_mqtt',
  ...
)

# Used for storage certs and keys
MQTT_CERTS_ROOT = /path/to/private/certs/storage
# Test Example: MQTT_CERTS_ROOT = os.path.join(BASE_DIR, 'private')
# Optional MQTT_ACL_ALLOW indicated if must allow topic not asigned for the user 
MQTT_ACL_ALLOW = False
# Optional MQTT_ACL_ALLOW_ANONIMOUS indicated if must allow topic not valid users
MQTT_ACL_ALLOW_ANONIMOUS = MQTT_ACL_ALLOW
```


Setting Up
==========
Browser to your admin page and configure: broken servers, auth and client data.

You can add the following code for send MQTTData model when new one are created:
```
from django.db.models.signals import post_save
from django_mqtt.models import MQTTData

def update_mqtt_data(sender, **kwargs):
    obj = kwargs["instance"]
    if isinstance(obj, MQTTData):
        if kwargs["created"]:
            obj.update_remote()
post_save.connect(receiver=update_mqtt_data, sender=MQTTData, dispatch_uid='django_mqtt_update_signal')
```

Or you can auto-send with any change using:
```
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_mqtt.models import MQTTData

@receiver(post_save, sender=MQTTData)
def auto_update(sender, instance, **kwargs):
    instance.update_remote()
```

Attach signals
==============
You can also attach django Signals for monitoring publisher, connection and disconnection.
```
from django_mqtt.models import *
from django_mqtt.signals import *

def before_connect(sender, client):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_connect.connect(receiver=before_connect, sender=MQTTServer, dispatch_uid='my_django_mqtt_before_connect')

def before_publish(sender, client, topic, payload, qos, retain):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_pre_publish.connect(receiver=before_publish, sender=MQTTData, dispatch_uid='my_django_mqtt_before_publish')

def then_publish(sender, client, userdata, mid):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_publish.connect(receiver=then_publish, sender=MQTTClient, dispatch_uid='my_django_mqtt_then_publish')

def then_disconnect(sender, client, userdata, rc):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_disconnect.connect(receiver=then_disconnect, sender=MQTTServer, dispatch_uid='my_django_mqtt_then_disconnect')
```


Configure Mosquitto for use Django Auth
=======================================
Thanks to [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug) you can configure Mosquitto for connect
with externals Auth systems.

For active Django Auth system edit your ```urls.py``` and add:
```
urlpatterns = patterns(
    ...
    url(r'^mqtt/', include('django_mqtt.mosquitto.auth_plug.urls')),
    ...
)
```

Run script [install_mosquitto_auth_plugin.sh](script/install_mosquitto_auth_plugin.sh) for install mosquitto server and
run script [compile_mosquitto_auth_plugin.sh](script/compile_mosquitto_auth_plugin.sh)
and [configure_mosquitto_auth_plugin.sh](script/configure_mosquitto_auth_plugin.sh) for
configure it for use [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug) with compiler configuration in
[config.mk](script/config.mk) and mosquitto configuration server with [auth_plug.conf](script/auth_plug.conf).


MQTT Test Brokens
=================
You can use the [mosquitto test server](http://test.mosquitto.org/) ```test.mosquitto.org```.
See the [mosquitto test server website](http://test.mosquitto.org/) for information about the broken configuration


Setup your own MQTT for test
============================
Run scripts [INSTALL.sh](test_web/INSTALL.sh) ```bash test_web/INSTALL.sh```
and [CONFIGURE.sh](test_web/CONFIGURE.sh) ```bash test_web/CONFIGURE.sh```.

This script will be install and configure [mosquitto](http://www.mosquitto.org/),
[mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug), [gunicorn](http://www.gunicorn.org/),
 [supervisord](http://www.supervisord.org/), [nginx](http://www.nginx.org/) and [postgresql](http://www.postgresql.org/)
