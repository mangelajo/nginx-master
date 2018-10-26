#!/usr/bin/python
import random
import time

from dns import resolver
from oslo_config import cfg
from oslo_log import log as logging

from nginx_master import dns_manager
from nginx_master.flows import base
from nginx_master.nginx_vserver import NginxVirtualServer
from nginx_master import postfix

LOG = logging.getLogger(__name__)


class DomainFlow(base.Flow):
    def __init__(self, domain_name, ip_address):
        super(DomainFlow, self).__init__(domain_name)

        self.server_name = domain_name
        d_parts = domain_name.split('.')
        if len(d_parts) == 2:
            self.domain_name = domain_name
            self.subdomain = ""
        else:
            self.domain_name = '.'.join(d_parts[1:3])
            self.subdomain = d_parts[0]

        self.next(self.initial_delay)
        self.backends = []
        self.nginx_vserver = NginxVirtualServer(domain_name, [])
        self.dkim_key = postfix.DKIMKey(domain_name)
        self.dns_api = dns_manager.Domain(self.domain_name)
        self.ip_address = ip_address

    def event_ip_changed(self, ip_address):
        self.ip_address = ip_address
        LOG.info("**** IP address changed: %s", ip_address)
        self.next_on_wait(self.check_dns)

    def set_backends(self, backends):
        self.backends = backends
        self.nginx_vserver.set_backends(backends)
        self.nginx_vserver.write_config()

    def initial_delay(self):
        delay = random.randint(5, 60)
        LOG.info("Starting delay for %s of %d seconds", self.server_name, delay)
        time.sleep(delay)
        self.next(self.write_config)

    def write_config(self):
        self.nginx_vserver.write_config()
        self.next(self.check_dns)

    @property
    def dns_reg_value(self):
	ip_a = cfg.CONF.dns_reg_value
	ip_a = ip_a.replace('IP_ADDRESS', self.ip_address)
	return ip_a

    def check_dns(self):
        try:
            records = self.dns_api.records
        except dns_manager.DomainNotFound:
            LOG.error("Your domain (%s) is not registered in the OVH api, "
                      "please go to "
                      "https://www.ovh.com/manager/web/index.html#/configuration/new_dns_zone?tab=GENERAL_INFORMATIONS",
                      self.domain_name)
            self.next(self.check_dns)
            return self.wait(60 * 10)

        key, entry_type, value = self.dkim_key.dns_entry
        LOG.debug("%s DNS API records: %s", self.domain_name, records)
        if (cfg.CONF.dns_reg_type, self.dns_reg_value) in records and \
                (key, value) in records:
            LOG.debug("dns records for %s already set, waiting for dns to be "
                      "ready", self.domain_name)
            self.next(self.wait_dns)
        else:
            self.records = records
            self.next(self.set_dns)

    def set_dns(self):

        self.dns_api.set_record(self.subdomain,
                                cfg.CONF.dns_reg_type,
                                self.dns_reg_value,
                                cfg.CONF.dns_reg_ttl)

        if self.subdomain != "":
            # setup the DKIM email signature key
            dkim_key, dkim_type, dkim_value = self.dkim_key.dns_entry
            self.dns_api.set_record(dkim_key, dkim_type, dkim_value)

            # setup the MX entry if configured
            if cfg.CONF.dns_mx:
                self.dns_api.set_record('', dns_manager.MX, cfg.CONF.dns_mx)

            # setup the SPF entry if configured
            if cfg.CONF.dns_spf:
                self.dns_api.set_record('', dns_manager.SPF,
                                        cfg.CONF.dns_spf,
                                        cfg.CONF.dns_spf_ttl)
            # setup the DMARC entry if configured
            if cfg.CONF.dns_dmarc:
                self.dns_api.set_record('_dmarc', dns_manager.TXT,
                                        cfg.CONF.dns_dmarc)

        self.next(self.wait_dns)

    def wait_dns(self):
        try:
            values = dns_manager.resolve(self.server_name, cfg.CONF.dns_reg_type)
            if len(values) == 1 and str(values[0]) == self.dns_reg_value:
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
                 self.dns_reg_value)

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
        if self.nginx_vserver.needs_cert_renewal:
            self.next(self.renew_cert)
        else:
            self.next(self.wait_renewal)
            return self.wait(60*10)

    def renew_cert(self):
        if self.nginx_vserver.create_certificate(renew=True):
            self.nginx_vserver.reload()
            self.next(self.wait_renewal)
        else:
            self.next(self.wait_renewal_retry)

    def wait_renewal_retry(self):
        LOG.error("Certificate renewal failed for %s, waiting 10 minutes",
                  self.domain_name)
        self.next(self.renew_cert)
        return self.wait(60*10)
