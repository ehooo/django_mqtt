from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from django_mqtt.publisher.models import Client, Topic, Data


class Command(BaseCommand):
    help = str(_('Connect with client and publish, for test proposed'))

    def add_arguments(self, parser):
        parser.add_argument('topic', action='store',
                            type=str, default=None,
                            help=str(_('Publisher topic'))
                            )
        parser.add_argument('payload', action='store',
                            type=str, default=None,
                            help=str(_('Payload'))
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
        topic = Topic(name=options['topic'])
        try:
            client = Client.objects.get(pk=db_client_id)
            data = Data(client=client, topic=topic, qos=options['qos'])
            data.payload = options['payload']
            data.update_remote()
        except Client.DoesNotExist:
            raise CommandError(str(_('Client not exist')))
