# -*- coding: utf-8 -*-
import os.path
import os


from oslo_config import cfg
import jinja2
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

CONF_PREFIX = 'auto-'
CONFD_DIR = '/etc/nginx/conf.d/auto-'

CONFIG_TEMPLATE = jinja2.Template(u"""
upstream {{ server.name | replace('.', '-') }} {
	{% for backend in server.backends %} server {{ backend }};{% endfor %}
}

server {
    listen 80;
    server_name {{ server.name }};
    access_log /var/log/nginx/{{ server.name }}.access.log combined;
    error_log /var/log/nginx/{{ server.name }}.access.log;
    location ^~ /.well-known/acme-challenge/ {
            default_type "text/plain";
            root /var/www/{{ server.name }}/;
            allow all;
            auth_basic off;
    }

    location / {
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_pass http://{{ server.name | replace('.', '-') }};
            proxy_set_header Authorization "";
    }
}

{% if server.ssl %}
server {
    # listen 443 ssl;
    listen 443 ssl http2;

    server_name {{ server.name }};

    ssl_certificate /etc/letsencrypt/live/{{ server.name }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ server.name }}/privkey.pem;

    ssl_stapling on;
    ssl_stapling_verify on;
    {% if server.strict_ssl %}add_header Strict-Transport-Security "max-age=31536000";{% endif %}

    access_log /var/log/nginx/{{ server.name }}.https.log combined;

    # maintain the .well-known directory alias for renewals
    location ^~ /.well-known {
        alias /var/www/{{ server.name }}/.well-known;
    }

    location / {
            proxy_pass http://{{ server.name | replace('.', '-') }};
            proxy_next_upstream error timeout invalid_header http_500 http_502
                                http_503 http_504;
            proxy_redirect off;
            proxy_buffering off;
            proxy_set_header Host            $host;
            proxy_set_header X-Real-IP       $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
    }
}
{% endif %}""")



class NginxVirtualServer:
    def __init__(self, domain_name, backends):
        self._domain_name = domain_name
        self._backends = backends
        self._id = domain_name.replace('.', '-')

    @property
    def has_cert(self):
        domain_dir = os.path.join(cfg.CONF.letsencrypt.cert_path,
                                  self._domain_name)
        return os.path.isfile(os.path.join(domain_dir, 'fullchain.pem')) and \
               os.path.isfile(os.path.join(domain_dir, 'privkey.pem'))

    @staticmethod
    def _ensure_directory(path):
        if not os.path.exists(path):
            os.makedirs(path)

    def create_certificate(self):
        static_path = "/var/www/%s" % self._domain_name

        self._ensure_directory(static_path)

        return os.system("certbot certonly --webroot -w %s " % static_path +
                         "--email %s -q --agree-tos -d %s" %
                         (cfg.CONF.letsencrypt.email, self._domain_name)) == 0

    @staticmethod
    def _ctl(action='reload'):
        os.system('service nginx %s' % action)

    @classmethod
    def reload(cls):
        cls._ctl('reload')

    @classmethod
    def restart(cls):
        cls._ctl('restart')

    @staticmethod
    def _write_file(path, contents):
        current_contents = None
        if os.path.isfile(path):
            current_contents = open(path, 'r').read()

        if current_contents != contents:
            LOG.debug("contents for path %s changed", path)
            LOG.debug("FROM:\n%s", current_contents)
            LOG.debug("\n\nTO:\n%s", contents)

            with open(path, 'w') as f:
                f.write(contents)
            return True
        else:
            LOG.debug("contents for path %s didn't change", path)

        return False

    @property
    def conf_file(self):
        return os.path.join(cfg.CONF.nginx.confd_path,
                            CONF_PREFIX + self._domain_name + '.conf')

    def write_config(self, strict_ssl=False):
        server = {'ssl': self.has_cert,
                  'id': self._id,
                  'name': self._domain_name,
                  'strict_ssl': strict_ssl,
                  'backends': self._backends}

        result_conf = CONFIG_TEMPLATE.render(
            server=server
            ).encode('utf-8')

        changed = self._write_file(self.conf_file, result_conf)

        if changed:
            self.reload()
        return changed
