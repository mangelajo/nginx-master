#!/usr/bin/python
import etcd
import eventlet
from oslo_config import cfg
from oslo_log import log as logging
import time

import config
from nginx_vserver import NginxVirtualServer
from flows import domain


LOG = logging.getLogger(__name__)
threads = {}


def setup():
    eventlet.monkey_patch()
    logging.register_options(cfg.CONF)
    config.setup()
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

            try:
                backends = client.get(server_path.key + "/backends")
            except etcd.EtcdKeyNotFound:
                LOG.error("No backends found for server %s", domain_name)

            for backend in backends.children:
                LOG.debug("found backend %s with value: %s", backend.key,
                          backend.value)

                value = backend.value.split('\n')[0]

                if ':' not in value:
                    value += u':80'

                server_backends.append(value)

            if domain_name in threads:
                domain_thread = threads[domain_name]
                domain_thread.set_backends(server_backends)
            else:
                LOG.info("Creating DomainFlow(%s)", domain_name)
                domain_thread = domain.DomainFlow(domain_name)
                domain_thread.set_backends(server_backends)
                threads[domain_name] = domain_thread
                domain_thread.run()


            if server_backends:
                virtual_server = NginxVirtualServer(domain_name, server_backends)
                virtual_server.write_config()

                if not virtual_server.has_cert:
                    if domain_name not in failed:
                        if not virtual_server.create_certificate():
                            failed[domain_name] = True
                        else:
                            if virtual_server.write_config():
                                LOG.info("Config file updated for server %s"
                                         " with backends: %s", domain_name,
                                         server_backends)

                    else:
                        LOG.error("%s in failed state, ignoring for now!",
                                  domain_name)
        time.sleep(cfg.CONF.loop_interval)

def main():
    setup()
    main_loop()

if __name__ == '__main__':
    main()