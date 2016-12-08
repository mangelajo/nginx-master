# -*- coding: utf-8 -*-
import unittest
import mock
import sys

from oslo_config import cfg

from nginx_master import nginx_vserver
from nginx_master import config

TEST_DOMAIN = 'test.es'
TEST_BACKENDS = ['192.168.1.1:80', '192.168.1.2:80']
TEST_PATH = '/path/myfile.txt'
TEST_CONTENT = 'this_is_a_test_content'

TEST_CONF_OUTPUT_NOCERT = """
upstream test-es {
	 server 192.168.1.1:80; server 192.168.1.2:80;
}

server {
    listen 80;
    server_name test.es;
    access_log /var/log/nginx/test.es.access.log combined;
    error_log /var/log/nginx/test.es.access.log;
    location ^~ /.well-known/acme-challenge/ {
            default_type "text/plain";
            root /var/www/test.es/;
            allow all;
            auth_basic off;
    }

    location / {
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_pass http://test-es;
            proxy_set_header Authorization "";
    }
}

"""

TEST_CONF_OUTPUT_CERT = TEST_CONF_OUTPUT_NOCERT + (
    """
server {
    # listen 443 ssl;
    listen 443 ssl http2;

    server_name test.es;

    ssl_certificate /etc/letsencrypt/live/test.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/test.es/privkey.pem;

    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security "max-age=31536000";

    access_log /var/log/nginx/test.es.https.log combined;

    # maintain the .well-known directory alias for renewals
    location ^~ /.well-known {
        alias /var/www/test.es/.well-known;
    }

    location / {
            proxy_pass http://test-es;
            proxy_next_upstream error timeout invalid_header http_500 http_502
                                http_503 http_504;
            proxy_redirect off;
            proxy_buffering off;
            proxy_set_header Host            $host;
            proxy_set_header X-Real-IP       $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
""")

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        mock.patch('sys.argv', sys.argv[0:1]).start()
        config.reset()
        config.setup()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(cfg.CONF.reset)



class TestNginxVserver(BaseTestCase):

    def setUp(self):
        self.os_system = mock.patch('os.system').start()
        super(TestNginxVserver, self).setUp()
        self._vserver = nginx_vserver.NginxVirtualServer(TEST_DOMAIN,
                                                         TEST_BACKENDS)

    def test_reload(self):
        self._vserver.reload()
        self.os_system.assert_called_once_with('service nginx reload')

    def test_restart(self):
        self._vserver.restart()
        self.os_system.assert_called_once_with('service nginx restart')


    @mock.patch('os.path.isfile')
    @mock.patch('nginx_master.nginx_vserver.open')
    def test__write_file_creates(self, open_mock, isfile_mock):
        open_mock.return_value = mock.MagicMock(spec=file)
        isfile_mock.side_effect = [False]
        result = self._vserver._write_file(TEST_PATH, TEST_CONTENT)

        open_mock.assert_called_once_with(TEST_PATH, 'w')
        file_mock = open_mock.return_value.__enter__.return_value
        file_mock.write.assert_called_once_with(TEST_CONTENT)
        self.assertTrue(result)

    @mock.patch('os.path.isfile')
    @mock.patch('nginx_master.nginx_vserver.open')
    def test__write_file_updates(self, open_mock, isfile_mock):
        file_mock = mock.MagicMock(spec=file)
        open_mock.return_value = file_mock
        isfile_mock.side_effect = [True]
        file_mock.read.side_effect = TEST_CONTENT + 'a'

        result = self._vserver._write_file(TEST_PATH, TEST_CONTENT)

        file_w_mock = file_mock.__enter__.return_value
        file_w_mock.write.assert_called_once_with(TEST_CONTENT)
        self.assertTrue(result)

    @mock.patch('os.path.isfile')
    @mock.patch('nginx_master.nginx_vserver.open')
    def test__write_file_equal(self, open_mock, isfile_mock):
        file_mock = mock.MagicMock(spec=file)
        open_mock.return_value = file_mock
        isfile_mock.side_effect = [True]
        file_mock.read = mock.Mock(side_effect=[TEST_CONTENT])

        result = self._vserver._write_file(TEST_PATH, TEST_CONTENT)


        file_w_mock = file_mock.__enter__.return_value
        file_w_mock.write.assert_not_called()
        self.assertFalse(result)

    def test_conf_file(self):
        self.assertEqual(self._vserver.conf_file,
                         "/etc/nginx/conf.d/auto-" + TEST_DOMAIN + ".conf")

    def test_write_config(self):
        with mock.patch(
                'nginx_master.nginx_vserver.NginxVirtualServer.has_cert',
                new_callable=mock.PropertyMock) as has_cert:
            has_cert.return_value = False

            self._vserver._write_file = mock.Mock()
            self._vserver.write_config(strict_ssl=False)
            self._vserver._write_file.assert_called_once_with(
                self._vserver.conf_file, TEST_CONF_OUTPUT_NOCERT)

    def test_write_config_with_cert(self):
        with mock.patch(
                'nginx_master.nginx_vserver.NginxVirtualServer.has_cert',
                new_callable=mock.PropertyMock) as has_cert:
            has_cert.return_value = True

            self._vserver._write_file = mock.Mock()
            self._vserver.write_config(strict_ssl=True)
            self._vserver._write_file.assert_called_once_with(
                self._vserver.conf_file, TEST_CONF_OUTPUT_CERT)
