#!/usr/bin/python
import etcd
from oslo_config import cfg
import time

import config
import dns_manager
from nginx_vserver import NginxVirtualServer


def main():
    config.setup()

    client = etcd.Client(port=cfg.etcd.port)
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

            print domain_name, ':'
            backends = client.get(server_path.key + "/backends")
            for backend in backends.children:
                print '   -', backend.key, ':', backend.value

                value = backend.value.split('\n')[0]

                if not value.endswith(':80'):
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
                        print domain_name, "in failed state, ignoring for now!"
        time.sleep(5)
