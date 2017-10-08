from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from django_mqtt.publisher.models import Client, Data
from django_mqtt.models import Topic, ClientId


class Command(BaseCommand):
    help = unicode(_('Connect with client as subscriber, for real time update proposed'))
    client_db = None
    create_if_not_exist = False
    use_update = False

    def add_arguments(self, parser):
        parser.add_argument('topic', action='store',
                            type=str, default=None,
                            help=unicode(_('Subcribe topic'))
                            )
        parser.add_argument('--id', action='store',
                            type=int, default=None, dest='id',
                            help=unicode(_('id from DB object'))
                            )
        parser.add_argument('--qos', action='store',
                            type=int, default=0, dest='qos',
                            help=unicode(_('Quality of Service'))
                            )
        parser.add_argument('--client_id', action='store',
                            type=str, default=None, dest='client_id',
                            help=unicode(_('client_id for broken'))
                            )
        parser.add_argument(
            '--update', action='store_true', type=bool, default=False, dest='update',
            help=unicode(_('Use update method to save the updates, this will not run the django signals'))
        )

    def handle(self, *args, **options):
        if not options['topic']:
            raise CommandError(unicode(_('Topic requiered and must be only one')))
        apply_filter = {}
        self.use_update = options['update']
        db_client_id = options['id']
        if db_client_id is None:
            if options['client_id']:
                apply_filter['client_id'] = options['client_id']
            clients = Client.objects.filter(**apply_filter)
            if clients.count() == 1:
                db_client_id = clients.all()[0].pk
            else:
                if clients.all().count() == 0:
                    raise CommandError(unicode(_('No client on DB')))
                print 'id -> client'
                for obj in clients.all():
                    print obj.pk, '\t->', obj
                db_client_id = input("Select id from DB: ")
        try:
            client_db = Client.objects.get(pk=db_client_id)
            cli = client_db.get_mqtt_client()

            cli.on_message = self.on_message
            cli.connect(client_db.server.host, client_db.server.port, client_db.keepalive)
            cli.subscribe(options['topic'], options['qos'])
            cli.loop_forever()
            cli.disconnect()
        except Client.DoesNotExist:
            raise CommandError(unicode(_('Client not exist')))

    def on_message(self, client, userdata, message):
        if not self.client_db:
            return

        topics = Topic.objects.filter(name=message.topic)
        topic = None
        if topics.exists():
            topic = topics.get()
        else:
            if self.create_if_not_exist:
                topic = Topic.objects.create(name=message.topic)
        if not topic:
            return

        datas = Data.objects.filter(topic=topic, qos=message.qos, client=self.client_db)
        data = None
        if datas.count() == 1:
            data = datas.get()
        else:
            if self.create_if_not_exist:
                data = Data.objects.create(topic=topic, qos=message.qos, client=self.client_db)
        if data:
            if self.use_update:
                Data.objects.filter(pk=data.pk).update(payload=message.payload)
            else:
                data.payload = message.payload
                data.save()
