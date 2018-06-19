Django-MQTT [![Build Status](https://travis-ci.org/ehooo/django_mqtt.svg?branch=master)](https://travis-ci.org/ehooo/django_mqtt)
===========
It is a django module that allow your:
- Mosquito Auth configured with [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug)
- Automatic MQTT replay


Install
=======
Install the latest version through pip
```
pip install -e git+https://github.com/ehooo/django_mqtt.git#egg=django_mqtt
```

Edit ```settings.py``` and add:
```
INSTALLED_APPS = (
  ...
  'django.contrib.admin',
  'django.contrib.auth',
  ...
  'django_mqtt',
  'django_mqtt.mosquitto.auth_plugin',
  'django_mqtt.publisher',
  ...
)

# Used for storage certs and keys if 'django_mqtt.publisher' is Installed
MQTT_CERTS_ROOT = /path/to/private/certs/storage
# Test Example: MQTT_CERTS_ROOT = os.path.join(BASE_DIR, 'private')

# Used for 'django_mqtt' if 'django_mqtt.mosquitto.auth_plugin' is Installed
# Optional MQTT_ACL_ALLOW indicated if must allow topic not asigned for the user 
MQTT_ACL_ALLOW = False
# Optional MQTT_ACL_ALLOW_ANONIMOUS indicated if must allow topic not valid users
MQTT_ACL_ALLOW_ANONIMOUS = MQTT_ACL_ALLOW

```

Also need to run migrations once
```
python manage.py migrate
```


Setting Up
==========
Browser to your admin page and configure: broken servers, auth and client data.

You can add the following code for send Data model when new one are created:
```
from django.db.models.signals import post_save
from django_mqtt.publisher.models import Data as MQTTData

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
from django_mqtt.publisher.models import Data as MQTTData

@receiver(post_save, sender=MQTTData)
def auto_update(sender, instance, **kwargs):
    instance.update_remote()
```

Attach signals
==============
You can also attach django Signals for monitoring publisher, connection and disconnection.
```
from django_mqtt.publisher.models import *
from django_mqtt.publisher.signals import *

def before_connect(sender, client):
    if not isinstance(client, Client):
        raise AttributeError('client must be Client object')
mqtt_connect.connect(receiver=before_connect, sender=Server, dispatch_uid='my_django_mqtt_before_connect')

def before_publish(sender, client, topic, payload, qos, retain):
    if not isinstance(client, Client):
        raise AttributeError('client must be Client object')
mqtt_pre_publish.connect(receiver=before_publish, sender=Data, dispatch_uid='my_django_mqtt_before_publish')

def then_publish(sender, client, userdata, mid):
    if not isinstance(client, Client):
        raise AttributeError('client must be Client object')
mqtt_publish.connect(receiver=then_publish, sender=Client, dispatch_uid='my_django_mqtt_then_publish')

def then_disconnect(sender, client, userdata, rc):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_disconnect.connect(receiver=then_disconnect, sender=Server, dispatch_uid='my_django_mqtt_then_disconnect')
```


Configure Mosquitto for use Django Auth
=======================================
Thanks to [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug) you can configure Mosquitto for connect
with externals Auth systems.

For active Django Auth system edit your ```urls.py``` and add:
```
urlpatterns = patterns(
    ...
    url(r'^mqtt/', include('django_mqtt.mosquitto.auth_plugin.urls')),
    ...
)
```

Run script [install_mosquitto_auth_plugin.sh](script/install_mosquitto_auth_plugin.sh) for install mosquitto server and
run script [compile_mosquitto_auth_plugin.sh](script/compile_mosquitto_auth_plugin.sh)
and [configure_mosquitto_auth_plugin.sh](script/configure_mosquitto_auth_plugin.sh) for
configure it for use [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug) with compiler configuration in
[config.mk](script/config.mk) and mosquitto configuration server with [auth_plug.conf](script/auth_plug.conf).

How Mosquitto Auth works ?
==========================
You could create the follow settings to set the default auth flow:
```
MQTT_ACL_ALLOW = False  # For allow auth users to any topic, False by defauld
MQTT_ACL_ALLOW_ANONIMOUS = False # For allow anonimous users, False by defauld
```
The auth mechanism works based con ACL class.

This mean that you could "bypass" the setting creating a wildcard topic (#).
For example, if you want that all auth user could subscribe but not publish:
```
from django_mqtt.models import Topic, ACL
from django_mqtt.models import PROTO_MQTT_ACC_SUS, PROTO_MQTT_ACC_PUB
topic = Topic.objects.create(name='#')
acl = ACL.objects.create(acc=PROTO_MQTT_ACC_PUB, topic=topic, allow=False)
```
If you want that only one user or group could publish to any topic, you could add it:
```
acl.allow=True
acl.users.add(User.objects.get(username='admin')
acl.groups.add(Group.objects.get(username='mqtt')
acl.save()
```

How user for publish data con MQTT server ?
===========================================
All this steps could be done by shell or by admin page
1. Create a MQTT Server
 ```
 from django_mqtt.publisher.models import Server
 mqtt_server = Server.objects.create(host='test.mosquitto.org')
 ```
2. Create a MQTT client
 ```
 from django_mqtt.publisher.models import Client
 mqtt_client = Client.objects.create(server=mqtt_server)
 ```
3. Create a MQTT Topic
 ```
 from django_mqtt.models import Topic
 mqtt_topic = Topic.objects.create(name='/django/MQTT')
 ```
4. Create a MQTT Data object
 ```
 from django_mqtt.publisher.models import Data
 mqtt_data = Data.objects.create(client=mqtt_client, topic=mqtt_topic, payload='initial data')
 mqtt_data.update_remote()  # Send/update data to MQTT server
 ```

# How to update data from remote MQTT?
1. Create a MQTT Server
 ```
 from django_mqtt.publisher.models import Server
 mqtt_server = Server.objects.create(host='test.mosquitto.org')
 ```
2. Create a MQTT client
 ```
 from django_mqtt.publisher.models import Client
 mqtt_client = Client.objects.create(server=mqtt_server)
 ```
3. Run command mqtt_updater
 ```
 python manage.py mqtt_updater /topic/#
 ```


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
