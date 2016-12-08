#!/usr/bin/python
import etcd
from oslo_config import cfg
from oslo_log import log as logging
import time

import config
import dns_manager
from nginx_vserver import NginxVirtualServer


LOG = logging.getLogger(__name__)


# Oslo Logging uses INFO as default
LOG.info("Oslo Logging")
LOG.warning("Oslo Logging")
LOG.error("Oslo Logging")


def setup():
    config.setup()
    logging.register_options(cfg.CONF)
    logging.setup(cfg.CONF, "nginx-master")

def main_loop():
    client = etcd.Client(port=cfg.CONF.etcd.port)
    failed = {}

    while True:
        try:
            directory = client.get("/servers/")
        except etcd.EtcdKeyNotFound:
            continue
        # loop through directory children
        for server_path in directory.children:
            domain_name = server_path.key.split('/')[-1]

            server_backends = []

            LOG.debug("domain_name %s", domain_name)

            backends = client.get(server_path.key + "/backends")
            for backend in backends.children:
                LOG.debug("found backend %s with value: %s", backend.key,
                          backend.value)

                value = backend.value.split('\n')[0]

                if ':' not in value:
                    value += u':80'

                server_backends.append(value)

                virtual_server = NginxVirtualServer(domain_name, server_backends)
                virtual_server.write_config()

                if not virtual_server.has_cert:
                    if domain_name not in failed:
                        if not virtual_server.create_certificate():
                            failed[domain_name] = True
                        else:
                            virtual_server.write_config()
                    else:
                        LOG.error("%s in failed state, ignoring for now!",
                                  domain_name)
        time.sleep(cfg.CONF.loop_interval)


if __name__ == '__main__':
    setup()
    main_loop()