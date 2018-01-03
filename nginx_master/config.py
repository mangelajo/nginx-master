import sys

from oslo_config import cfg

import dns_manager


common_options = [
    cfg.StrOpt('dns_reg_type', default=dns_manager.A),
    cfg.StrOpt('dns_reg_value', default="IP_ADDRESS"),
    cfg.IntOpt('dns_reg_ttl', default=900, help='TTL for the record'),
    cfg.StrOpt('dns_spf', default="v=spf1 a:cpanel.optimizacionweb.es -all"),
    cfg.StrOpt('dns_mx', default="300 redirect.ovh.net."),
    cfg.IntOpt('dns_spf_ttl', default=900, help='TTL for the SPF record'),
    cfg.IntOpt('loop_interval', default=5, help='Interval between loops'),
    cfg.StrOpt('dns_dmarc', default="v=DMARC1;p=reject;pct=100;"
                                     "rua=mailto:miguelangel@ajo.es")
]


etcd_options = [
    cfg.PortOpt('port', help='etcd server port number',
                default=2379),
    cfg.HostnameOpt('hostname', default='localhost',
                    help='etcd server hostname')
]

letsencrypt_options = [
    cfg.StrOpt('email', help='The Letsencrypt account for your '
                             'certificates'),
    cfg.StrOpt('cert_path', default='/etc/letsencrypt/live/')
]

nginx_options = [
    cfg.StrOpt('confd_path', default='/etc/nginx/conf.d/'),
]

stun_options = [
    cfg.StrOpt('host', default='stun.l.google.com'),
    cfg.PortOpt('port', default=19302),
    cfg.IntOpt('check_interval', default=60)
]

def reset():
    cfg.CONF.reset()

def setup():
    cfg.CONF.register_opts(common_options)
    cfg.CONF.register_opts(letsencrypt_options, group='letsencrypt')
    cfg.CONF.register_opts(nginx_options, group='nginx')
    cfg.CONF.register_opts(etcd_options, group='etcd')
    cfg.CONF.register_opts(stun_options, group='stun')
    cfg.CONF()
