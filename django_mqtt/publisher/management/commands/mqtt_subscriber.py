from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from django_mqtt.publisher.models import Client


def on_connect(client, userdata, flags, rc):
    print("Hi", client._client_id, userdata, flags, rc)


def on_disconnect(client, userdata, rc):
    print("Bye", client._client_id, userdata, rc)


def on_message(client, userdata, message):
    print("Msg", client._client_id, userdata)
    print("mid", message.mid, "dup:", message.dup, "QoS:", message.qos)
    print("retain", message.retain, "state", message.state)
    print("timestamp", message.timestamp)
    print("topic", message.topic)
    print("payload", message.payload)
    print("=============================")


def on_publish(client, userdata, mid):
    print("Publish", client._client_id, userdata, mid)


def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribe", client._client_id, userdata, mid, granted_qos)


def on_unsubscribe(client, userdata, mid):
    print("Unsubscribe", client._client_id, userdata, mid)


def on_log(client, userdata, level, buf):
    print("Log", client._client_id, userdata, level, buf)


class Command(BaseCommand):
    help = str(_('Connect with client as subscriber, for test proposed'))

    def add_arguments(self, parser):
        parser.add_argument('topic', action='store',
                            type=str, default=None,
                            help=str(_('Subcribe topic'))
                            )
        parser.add_argument('--id', action='store',
                            type=int, default=None, dest='id',
                            help=str(_('id from DB object'))
                            )
        parser.add_argument('--qos', action='store',
                            type=int, default=0, dest='qos',
                            help=str(_('Quality of Service'))
                            )
        parser.add_argument('--client_id', action='store',
                            type=str, default=None, dest='client_id',
                            help=str(_('client_id for broken'))
                            )

    def handle(self, *args, **options):
        if not options['topic']:
            raise CommandError(str(_('Topic requiered and must be only one')))
        apply_filter = {}
        db_client_id = options['id']
        if db_client_id is None:
            if options['client_id']:
                apply_filter['client_id'] = options['client_id']
            clients = Client.objects.filter(**apply_filter)
            if clients.count() == 1:
                db_client_id = clients.all()[0].pk
            else:
                if clients.all().count() == 0:
                    raise CommandError(str(_('No client on DB')))
                self.stdout.write('id -> client')
                for obj in clients.all():
                    self.stdout.write("{} \t-> {}".format(obj.pk, obj))
                db_client_id = input("Select id from DB: ")
        try:
            obj = Client.objects.get(pk=db_client_id)
            cli = obj.get_mqtt_client()

            cli.on_connect = on_connect
            cli.on_disconnect = on_disconnect
            cli.on_publish = on_publish
            cli.on_subscribe = on_subscribe
            cli.on_unsubscribe = on_unsubscribe
            cli.on_message = on_message
            cli.on_log = on_log
            cli.connect(obj.server.host, obj.server.port, obj.keepalive)
            cli.subscribe(options['topic'], options['qos'])
            cli.loop_forever()
            cli.disconnect()
        except Client.DoesNotExist:
            raise CommandError(str(_('Client not exist')))
