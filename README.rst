nginx-master
============

.. image:: https://img.shields.io/pypi/v/nginx-master.svg
        :target: https://pypi.python.org/pypi/nginx-master

.. image:: https://img.shields.io/pypi/pyversions/nginx-master.svg
         :target: https://pypi.python.org/pypi/nginx-master

.. image:: https://img.shields.io/:license-apache-blue.svg
         :target: http://www.apache.org/licenses/LICENSE-2.0

What is nginx-master?
~~~~~~~~~~~~~~~~~~~~~

nginx-master is a reverse proxy with ssl termination, automatic
certificate generation via letsencrypt, and automatic dns management.

This is useful if you have only one IP to listen to all your traffic
and many domains to serve via containers or VMs.

nginx-master will watch an etcd directory with the following format:

    /servers/{domain-name}/backends/{name}: IP:port


So for example, you could have:

    /servers/test-domain.es/backends/main: 192.168.1.1:80

    /servers/test-domain.es/backends/second: 192.168.1.2:80

    /servers/another-domain.com/backends/main: 192.168.2.1:80
