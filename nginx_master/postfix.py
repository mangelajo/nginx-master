#
# postfix manager to allow an exit path for transactional emails
#
#

import os
import re

from oslo_log import log as logging

LOG = logging.getLogger(__name__)

DKIM_KEY_CMD = "opendkim-genkey -b 2048 -h rsa-sha256 -r -s default -d %s"
DKIM_KEYTABLE = "/etc/opendkim/KeyTable"
DKIM_KEYTABLE_ENTRY = "default._domainkey.%(domain)s %(domain)s:default:" \
                      "/etc/opendkim/keys/%(domain)s/default.private"
DKIM_SIGNINGTABLE = "/etc/opendkim/SigningTable"
DKIM_SIGNINGTABLE_ENTRY = "*@%(domain)s default._domainkey.%(domain)s"

DKIM_KEY_DIR = "/etc/opendkim/keys/%s"
DKIM_KEY_PATH = DKIM_KEY_DIR + "/default.private"
DKIM_DNS_PATH = DKIM_KEY_DIR + "/default.txt"


class DKIMKey(object):
    def __init__(self, domain_name):
        self._domain = domain_name
        self._ensure_dir(self.key_dir)

    @staticmethod
    def _ensure_line(filename, line):
        lines = open(filename, 'r').readlines()
        for _line in lines:
            _line = _line.rstrip()
            if _line == line:
                return False

        with open(filename, 'a') as f:
            f.write(line + '\n')

        return True

    def _ensure_config(self):
        data = {'domain': self._domain}
        signing_entry = DKIM_SIGNINGTABLE_ENTRY % data
        keytable_entry = DKIM_KEYTABLE_ENTRY % data
        changed = (self._ensure_line(DKIM_SIGNINGTABLE, signing_entry) or
                   self._ensure_line(DKIM_KEYTABLE, keytable_entry))
        if changed:
            LOG.info("opendkim configured for domain (%s)", self._domain)
            self.reload()

    @staticmethod
    def _ctl(action='reload'):
        os.system('service opendkim %s' % action)

    @classmethod
    def reload(cls):
        cls._ctl('reload')

    @classmethod
    def restart(cls):
        cls._ctl('restart')


    @property
    def key_dir(self):
        return DKIM_KEY_DIR % self._domain

    @property
    def key_path(self):
        return DKIM_KEY_PATH % self._domain

    @property
    def dns_path(self):
        return DKIM_DNS_PATH % self._domain

    def _ensure_dir(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _generate_key(self):
        build_cmd = DKIM_KEY_CMD % self._domain
        os.system("cd %s; %s" % (self.key_dir, build_cmd))
        LOG.info('DKIM key generated for domain %s', self._domain)

    @property
    def dns_entry(self):
        if not os.path.exists(self.dns_path):
            self._generate_key()

        self._ensure_config()

        with open(self.dns_path, 'r') as f:
            data = f.read()
            key_data = ''.join(re.findall(r'"(.*?)"', data))
            return (data.split('\t')[0],
                    data.split('\t')[2],
                    key_data)