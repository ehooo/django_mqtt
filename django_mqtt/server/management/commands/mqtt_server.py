from __future__ import absolute_import

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.management.base import BaseCommand, CommandError
from django.utils.encoding import force_text, get_system_encoding

from django_mqtt.server.service import *
from django_mqtt.server.packets import *

from datetime import datetime
import socket
import errno
import ssl
import sys
import re
import os


naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)


class Command(BaseCommand):
    help = _('Server MQTT')

    default_port = '1883'
    default_ssl_port = '8883'
    is_running = False

    def add_arguments(self, parser):
        parser.add_argument('addrport', nargs='?',
                            help='Optional port number, or ipaddr:port')
        parser.add_argument('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
                            help='Tells Server to use an IPv6 address.')
        parser.add_argument('--nothreading', action='store_false', dest='use_threading', default=True,
                            help='Tells Django to NOT use threading.')
        parser.add_argument('--ssl', '-s', action='store_true', dest='use_ssl', default=False,
                            help='Tells Server to run with SSL.')
        parser.add_argument('--certfile', action='store', dest='certfile',
                            default=None, help='Required for SSL')
        parser.add_argument('--keyfile', action='store', dest='keyfile',
                            default=None, help='Required for SSL')
        parser.add_argument('--backlog', action='store', dest='backlog', type=int,
                            default=5, help='Maximum number of queued connections')

    def execute(self, *args, **options):
        if options.get('no_color'):
            # We rely on the environment because it's currently the only
            # way to reach WSGIRequestHandler. This seems an acceptable
            # compromise considering `runserver` runs indefinitely.
            os.environ[str("DJANGO_COLORS")] = str("nocolor")
        super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
        from django.conf import settings

        if not settings.DEBUG and not settings.ALLOWED_HOSTS:
            raise CommandError('You must set settings.ALLOWED_HOSTS if DEBUG is False.')

        if options.get('certfile') and options.get('keyfile'):
            options['use_ssl'] = True
        elif options.get('use_ssl'):
            raise CommandError('certfile and keyfile required for SSL')
        use_ssl = options.get('use_ssl')

        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self._raw_ipv6 = False
        if not options.get('addrport'):
            self.addr = ''
            if use_ssl:
                self.port = self.default_ssl_port
            else:
                self.port = self.default_port
        else:
            m = re.match(naiveip_re, options['addrport'])
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % options['addrport'])
            self.addr, _ipv4, _ipv6, _fqdn, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." % self.port)
            if self.addr:
                if _ipv6:
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                    self._raw_ipv6 = True
                elif self.use_ipv6 and not _fqdn:
                    raise CommandError('"%s" is not a valid IPv6 address.' % self.addr)
        if not self.addr:
            self.addr = '::1' if self.use_ipv6 else '127.0.0.1'
            self._raw_ipv6 = bool(self.use_ipv6)

        self.run(**options)

    def run(self, **options):
        self.is_running = True
        threading = options.get('use_threading')
        shutdown_message = options.get('shutdown_message', '')

        shutdown_message = options.get('shutdown_message', '')
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        self.stdout.write("Performing system checks...\n\n")

        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })

        now = datetime.utcnow().strftime('%B %d, %Y - %X')
        if six.PY2:
            now = now.decode(get_system_encoding())
        self.stdout.write(now)

        try:
            self.manage_connection(self.addr, int(self.port), backlog=options.get('backlog'),
                                   certfile=options.get('certfile'), keyfile=options.get('keyfile'),
                                   ipv6=self.use_ipv6, threading=threading)
        except socket.error as e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned to.",
            }
            try:
                error_text = ERRORS[e.errno]
            except KeyError:
                error_text = force_text(e)
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)

    def manage_connection(self, addr, port, certfile=None, keyfile=None, ipv6=False, threading=False, backlog=5):
        context = None
        bind_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if certfile and keyfile:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=certfile, keyfile=keyfile)
            bind_socket = socket.socket()
        bind_socket.bind((addr, port))
        bind_socket.listen(backlog)

        forks = []
        while self.is_running:
            try:
                sock, from_addr = bind_socket.accept()
                conn = sock
                if context:
                    conn = context.wrap_socket(sock, server_side=True)

                th = MqttServiceThread(conn)
                if threading:
                    th.start()
                    forks.append(th)
                else:
                    th.run()
            except Exception as ex:
                import traceback
                self.stdout.write(traceback.format_exc())
                self.stdout.write(str(ex))
            finally:
                pass
