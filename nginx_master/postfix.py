#
# postfix manager to allow an exit path for transactional emails
#
#

import os
import re


DKIM_KEY_CMD = "opendkim-genkey -b 2048 -h rsa-sha256 -r -s default -d %s"

DKIM_KEY_DIR = "/etc/opendkim/keys/%s"
DKIM_KEY_PATH = DKIM_KEY_DIR + "/default.private"
DKIM_DNS_PATH = DKIM_KEY_DIR + "/default.txt"


class DKIMKey(object):
    def __init__(self, domain_name):
        self._domain = domain_name
        self._ensure_dir(self.key_dir)

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

    @property
    def dns_entry(self):
        if not os.path.exists(self.dns_path):
            self._generate_key()

        with open(self.dns_path, 'r') as f:
            data = f.read()
            key_data = ''.join(re.findall(r'"(.*?)"', data))
            return (data.split('\t')[0],
                    data.split('\t')[2],
                    key_data)