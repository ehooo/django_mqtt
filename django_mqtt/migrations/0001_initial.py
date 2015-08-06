# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MQTTAuth',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.CharField(max_length=1024)),
                ('password', models.CharField(max_length=1024, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MQTTClient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('client_id', models.CharField(max_length=1024, null=True, blank=True)),
                ('keepalive', models.IntegerField(default=60)),
                ('clean_session', models.BooleanField(default=True)),
                ('auth', models.ForeignKey(blank=True, to='django_mqtt.MQTTAuth', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MQTTData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('topic', models.CharField(max_length=1024)),
                ('qos', models.IntegerField(default=0, choices=[(0, b'QoS 0: Delivered at most once'), (1, b'QoS 1: Always delivered at least once'), (2, b'QoS 2: Always delivered exactly once')])),
                ('payload', models.TextField(null=True, blank=True)),
                ('retain', models.BooleanField(default=False)),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(to='django_mqtt.MQTTClient')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MQTTSecureConf',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ca_certs', models.CharField(max_length=1024)),
                ('cert_reqs', models.IntegerField(default=2, choices=[(2, b'Required'), (1, b'Optional'), (0, b'None')])),
                ('tls_version', models.IntegerField(default=3, choices=[(3, b'v1'), (0, b'v2'), (2, b'v2.3'), (1, b'v3')])),
                ('certfile', models.FileField(storage=django.core.files.storage.FileSystemStorage(location=b'C:\\Users\\ehooo\\Documents\\GitHub\\django_mqtt\\private'), null=True, upload_to=b'certs', blank=True)),
                ('keyfile', models.FileField(storage=django.core.files.storage.FileSystemStorage(location=b'C:\\Users\\ehooo\\Documents\\GitHub\\django_mqtt\\private'), null=True, upload_to=b'keys', blank=True)),
                ('ciphers', models.CharField(default=None, max_length=1024, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MQTTServer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('host', models.CharField(max_length=1024, null=True, blank=True)),
                ('port', models.IntegerField(default=1883)),
                ('protocol', models.IntegerField(default=4, choices=[(3, b'v3.1'), (4, b'v3.1.1')])),
                ('status', models.IntegerField(default=6, choices=[(0, b'Connection successful'), (1, b'Connection refused - incorrect protocol version'), (2, b'Connection refused - invalid client identifier'), (3, b'Connection refused - server unavailable'), (4, b'Connection refused - bad username or password'), (5, b'Connection refused - not authorised'), (6, b'Unknow'), (100, b'Connection error'), (191, b'Connection error - Get address info failed'), (200, b'Connection error - The operation was interrupted'), (201, b'Connection error - Permission denied'), (202, b'Connection error - A fault occurred on the network'), (203, b'Connection error - An invalid operation was attempted'), (204, b'Connection error - The socket operation would block'), (205, b'Connection error - A blocking operation is already in progress'), (206, b'Connection error - The network address is in use'), (207, b'Connection error - The connection has been reset'), (208, b'Connection error - The network has been shut down'), (209, b'Connection error - The operation timed out'), (210, b'Connection error - Connection refused'), (211, b'Connection error - The name is too long'), (212, b'Connection error - The host is down'), (213, b'Connection error - The host is unreachable')])),
                ('secure', models.ForeignKey(blank=True, to='django_mqtt.MQTTSecureConf', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='mqttdata',
            unique_together=set([('client', 'topic')]),
        ),
        migrations.AddField(
            model_name='mqttclient',
            name='server',
            field=models.ForeignKey(to='django_mqtt.MQTTServer'),
            preserve_default=True,
        ),
    ]
