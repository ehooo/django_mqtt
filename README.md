Django-MQTT
===========
It is a django module that allow send your information stored in your database to MQTT server as MQTT Publisher.


Install
=======
Edit ```settings.py``` and add:
```
INSTALLED_APPS = (
  ...
  'django.contrib.admin',
  ...
  'django_mqtt',
  ...
)

# Used for storage certs and keys
PRIVATE_ROOT = /path/to/private/files/storage
# Test Example: PRIVATE_ROOT = os.path.join(BASE_DIR, 'private')
```


Setting Up
==========
Browser to your admin page and configure: broken servers, auth and client data.

Just add or edit a MQTTData model and the system will be send the information to the properly broken server.


Attach signals
==============
You can also attach django Signals for publisher and disconnection.
```
def on_disconnect(sender, client, userdata, rc):
    if not isinstance(obj, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_disconnect.connect(receiver=on_disconnect, sender=MQTTServer, dispatch_uid='my_django_mqtt_on_disconnect')

def on_publish(sender, client, userdata, mid):
    if not isinstance(obj, MQTTClient):
        raise AttributeError('client must be MQTTClient object')
mqtt_publish.connect(receiver=on_publish, sender=MQTTClient, dispatch_uid='my_django_mqtt_on_publish')
```

MQTT Test Brokens
=================
You can use the [mosquitto test server](http://test.mosquitto.org/) ```test.mosquitto.org```. See the [mosquitto test server website](http://test.mosquitto.org/) for information about the broken configuration


Configure Mosquitto for use Django Auth
=======================================
Thanks to [mosquitto-auth-plug](https://github.com/jpmens/mosquitto-auth-plug) you can configure Mosquitto for connect with externals Auth systems.

For active Django Auth system edit your ```urls.py``` and add:
```
urlpatterns = patterns(
    ...
    url(r'^mqtt/', include('django_mqtt.urls')),
    ...
)
```

For active Mosquito Auth Plugin edit ```mosquitto.conf``` and add:
```
auth_plugin /path/to/auth-plug.so

auth_opt_backends http
auth_opt_http_ip 127.0.0.1
auth_opt_http_port 8000
auth_opt_http_getuser_uri /mqtt/auth
auth_opt_http_superuser_uri /mqtt/superuser
auth_opt_http_aclcheck_uri /mqtt/acl
```
