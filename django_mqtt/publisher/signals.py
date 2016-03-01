from django.dispatch import Signal

mqtt_connect = Signal(providing_args=["client"])
mqtt_pre_publish = Signal(providing_args=["client", "topic", "payload", "qos", "retain"])
mqtt_publish = Signal(providing_args=["client", "userdata", "mid"])
mqtt_disconnect = Signal(providing_args=["client", "userdata", "rc"])
