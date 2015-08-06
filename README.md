Django-MQTT
===========
It is a django module that allow send your information stored in your database to MQTT server as MQTT Publisher.

Install
=======
Edit ´´´settings.py´´´ and add:
´´´
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
´´´

Setting Up
==========
Browser to your admin page and configure: broken servers, auth and client data.

Just add or edit a MQTTData model and the system will be send the information to the properly broken server.


Attach signals
==============
You can also attach django Signals for publisher and disconnection.
´´´
def on_disconnect(sender, client, userdata, rc):
    if isinstance(obj, MQTTClient):
        raise Att
mqtt_disconnect.connect(receiver=on_disconnect, sender=MQTTServer, dispatch_uid='my_django_mqtt_on_disconnect')

def on_publish(sender, client, userdata, mid):
    pass
mqtt_publish.connect(receiver=on_publish, sender=MQTTClient, dispatch_uid='my_django_mqtt_on_publish')

´´´
