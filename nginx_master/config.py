import sys

from oslo_config import cfg

import dns_manager


common_options = [
    cfg.StrOpt('dns_reg_type', default=dns_manager.A),
    cfg.StrOpt('dns_value', help='The value to use for the DNS settings'),
    cfg.IntOpt('loop_interval', default=5, help='Interval between loops')
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

def reset():
    cfg.CONF.reset()

def setup():
    cfg.CONF.register_opts(common_options)
    cfg.CONF.register_opts(letsencrypt_options, group='letsencrypt')
    cfg.CONF.register_opts(nginx_options, group='nginx')
    cfg.CONF.register_opts(etcd_options, group='etcd')
    cfg.CONF()