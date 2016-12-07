from oslo_config import cfg
import jinja2
import os.path
import os

CONF_PREFIX = 'auto-'
CONFD_DIR = '/etc/nginx/conf.d/auto-'


class NginxVirtualServer:
    def __init__(self, domain_name, backends):
        self._domain_name = domain_name
        self._backends = backends
        self._id = domain_name.replace('.', '-')
        self._conf_template = jinja2.Environment(
            loader=jinja2.FileSystemLoader([os.path.dirname(__file__)])
            ).get_template('nginx-server.conf.j2')

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
            with open(path, 'w') as f:
                f.write(contents)
            return True
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

        result_conf = self._conf_template.render(
            server=server
            ).encode('utf-8')

        changed = self._write_file(self.conf_file, result_conf)

        if changed:
            self.reload()
