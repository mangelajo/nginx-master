#!/usr/bin/python
from dns import resolver
from oslo_config import cfg
from oslo_log import log as logging

from nginx_master import dns_manager
from nginx_master.flows import base
from nginx_master.nginx_vserver import NginxVirtualServer

LOG = logging.getLogger(__name__)


class DomainFlow(base.Flow):
    def __init__(self, domain_name):
        super(DomainFlow, self).__init__(domain_name)
        self.domain_name = domain_name
        self.next(self.write_config)
        self.backends = []
        self.nginx_vserver = NginxVirtualServer(domain_name, [])

    def set_backends(self, backends):
        self.backends = backends
        self.nginx_vserver.set_backends(backends)
        self.nginx_vserver.write_config()

    def write_config(self):
        self.nginx_vserver.write_config()
        self.next(self.check_dns)

    def check_dns(self):
        dns_man = dns_manager.Domain(self.domain_name)
        try:
            records = dns_man.records
        except dns_manager.DomainNotFound:
            LOG.error("Your domain (%s) is not registered in the OVH api, "
                      "please go to "
                      "https://www.ovh.com/manager/web/index.html#/configuration/new_dns_zone?tab=GENERAL_INFORMATIONS",
                      self.domain_name)
            self.next(self.check_dns)
            return self.wait(60 * 10)
        if True:
            self.next(self.wait_dns)
        else:
            self.next(self.set_dns)

    def set_dns(self):
        self.next(self.wait_dns)

    def wait_dns(self):
        try:
            values = dns_manager.resolve(self.domain_name, cfg.CONF.dns_reg_type)
            if len(values)==1 and str(values[0]) == cfg.CONF.dns_reg_value:
                LOG.info("DNS for %s is correctly set", self.domain_name)
                if not self.nginx_vserver.has_cert:
                    return self.next(self.grab_cert)
                else:
                    return self.next(self.wait_renewal)

        except resolver.NoAnswer:
            pass

        LOG.info("Waiting for dns to be set for %s (%s: %s)",
                 self.domain_name,
                 cfg.CONF.dns_reg_type,
                 cfg.CONF.dns_reg_value)

        return self.wait(60)

    def grab_cert(self):
        if self.nginx_vserver.create_certificate():
            self.next(self.wait_renewal)
        else:
            self.next(self.wait_retry)

    def wait_retry(self):
        LOG.error("Certificate creation failed for %s, waiting 10 minutes",
                  self.domain_name)
        self.next(self.check_dns)
        return self.wait(60*10)

    def wait_renewal(self):
        self.next(self.wait_renewal)
        return self.wait(60*10)