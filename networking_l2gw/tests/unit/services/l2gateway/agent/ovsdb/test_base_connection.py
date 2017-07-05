# Copyright (c) 2015 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os.path
import socket
import ssl
import time

import eventlet
import mock
from neutron.tests import base
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_l2gw.services.l2gateway.agent import l2gateway_config as conf
from networking_l2gw.services.l2gateway.agent.ovsdb import base_connection
from networking_l2gw.services.l2gateway.agent.ovsdb import manager
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants as n_const

LOG = logging.getLogger(__name__)


class FakeConf(object):
    def __init__(self):
        self.use_ssl = False
        self.ovsdb_ip = '1.1.1.1'
        self.ovsdb_port = 6632


class FakeDecodeClass(object):
    def __init__(self, fake_data):
        self.fake_data = fake_data

    def decode(self, utf8):
        return self.fake_data


class SocketClass(object):
    def __init__(self,
                 connect_error=None,
                 send_error=None,
                 recv_error=None,
                 rcv_data=None):
        self.connect_error = connect_error
        self.rcv_data = rcv_data
        self.send_error = send_error
        self.recv_error = recv_error

    def connect(self, ip_port):
        if self.connect_error:
            raise self.connect_error

    def send(self, data):
        if self.send_error:
            raise self.send_error
        return len(data)

    def recv(self, length):
        if self.recv_error:
            raise self.recv_error
        return self.rcv_data

    def close(self):
        pass


class TestBaseConnection(base.BaseTestCase):
    def setUp(self):
        super(TestBaseConnection, self).setUp()

        self.conf = mock.patch.object(conf, 'L2GatewayConfig').start()
        config.register_ovsdb_opts_helper(cfg.CONF)
        cfg.CONF.set_override('max_connection_retries', 0, 'ovsdb')

        self.sock = mock.patch('socket.socket').start()
        self.ssl_sock = mock.patch.object(ssl, 'wrap_socket').start()
        self.l2gw_ovsdb = base_connection.BaseConnection(mock.Mock(),
                                                         self.conf)
        self.op_id = 'abcd'
        self.fake_message = {'id': self.op_id,
                             'fake_key': 'fake_value'}

        self.l2gw_ovsdb.responses = [self.fake_message]

    def test_init(self):
        """Test case to test __init__."""

        fakesocket = SocketClass()
        with mock.patch.object(base_connection.LOG, 'debug') as logger_call, \
                mock.patch.object(socket, 'socket',
                                  return_value=fakesocket):
            self.l2gw_ovsdb.__init__(mock.Mock(), self.conf)
            self.assertTrue(self.l2gw_ovsdb.connected)
            self.assertTrue(logger_call.called)
            self.assertTrue(self.sock.called)

    def test_init_with_socket_error(self):
        """Test case to test __init__ with socket error exception."""

        fakesocket = SocketClass(socket.error)
        with mock.patch.object(base_connection.LOG, 'exception') as logger_exc, \
                mock.patch.object(base_connection.LOG, 'warning') as logger_warn, \
                mock.patch.object(socket, 'socket', return_value=fakesocket) as sock_connect, \
                mock.patch.object(time, 'sleep'):
            ovsdb_conf = FakeConf()
            self.assertRaises(socket.error, base_connection.BaseConnection,
                              cfg.CONF.ovsdb, ovsdb_conf)
            self.assertTrue(logger_warn.called)
            self.assertTrue(logger_exc.called)
            self.assertTrue(sock_connect.called)

    def test_init_with_timeout(self):
        """Test case to test __init__ with socket timeout exception."""

        fakesocket = SocketClass(socket.timeout)
        with mock.patch.object(base_connection.LOG, 'exception') as logger_exc, \
                mock.patch.object(base_connection.LOG, 'warning') as logger_warn, \
                mock.patch.object(socket, 'socket', return_value=fakesocket) as sock_connect, \
                mock.patch.object(time, 'sleep'):
            ovsdb_conf = FakeConf()
            self.assertRaises(socket.timeout, base_connection.BaseConnection,
                              cfg.CONF.ovsdb, ovsdb_conf)
            self.assertTrue(logger_warn.called)
            self.assertTrue(logger_exc.called)
            self.assertTrue(sock_connect.called)

    def test_response(self):
        """Test case to test _response."""
        response = self.l2gw_ovsdb._response(self.op_id)
        self.assertIsNotNone(response)
        self.assertEqual(response, self.fake_message)

    def test_send(self):
        """Test case to test send."""
        with mock.patch.object(self.l2gw_ovsdb.socket, 'send',
                               side_effect=Exception) as send:
            with mock.patch.object(base_connection.LOG,
                                   'exception'):
                with mock.patch.object(self.l2gw_ovsdb,
                                       'disconnect') as mock_disconnect:
                    with mock.patch.object(base_connection.LOG,
                                           'warning'):
                        self.l2gw_ovsdb.send(mock.Mock())
                        self.assertTrue(send.called)
                        self.assertTrue(mock_disconnect.called)

    def test_disconnect(self):
        """Test case to test disconnect socket."""
        self.l2gw_ovsdb.monitor = True
        with mock.patch.object(self.l2gw_ovsdb.socket, 'close') as sock_close:
            self.l2gw_ovsdb.disconnect()
            self.assertTrue(sock_close.called)
            self.assertFalse(self.l2gw_ovsdb.connected)


class TestBaseConnection_with_enable_manager(base.BaseTestCase):
    def setUp(self):
        super(TestBaseConnection_with_enable_manager, self).setUp()

        self.conf = mock.patch.object(conf, 'L2GatewayConfig').start()
        config.register_ovsdb_opts_helper(cfg.CONF)
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.mgr = mock.patch.object(manager, 'OVSDBManager').start()
        self.l2gw_ovsdb_conn = base_connection.BaseConnection(
            mock.Mock(), self.conf, self.mgr)
        self.mock_sock = mock.patch('socket.socket').start()
        self.l2gw_ovsdb_conn.s = mock.patch('socket.socket').start()
        self.fakesocket = SocketClass()
        self.fake_ip = 'fake_ip'
        self.l2gw_ovsdb_conn.ovsdb_conn_list = ['fake_ip']
        self.l2gw_ovsdb_conn.ovsdb_dicts = {'fake_ip': self.fakesocket}

    def test_init_with_enable_manager(self):
        fake_dict = {}
        with mock.patch.object(eventlet.greenthread,
                               'spawn') as (mock_thread):
            self.l2gw_ovsdb_conn.__init__(mock.Mock(), self.conf)
            self.assertEqual(mock.ANY, self.l2gw_ovsdb_conn.s)
            self.assertFalse(self.l2gw_ovsdb_conn.check_sock_rcv)
            self.assertIsNone(self.l2gw_ovsdb_conn.check_c_sock)
            self.assertEqual(fake_dict, self.l2gw_ovsdb_conn.ovsdb_dicts)
            self.assertEqual(fake_dict, self.l2gw_ovsdb_conn.ovsdb_fd_states)
            self.assertEqual(6632,
                             self.l2gw_ovsdb_conn.manager_table_listening_port)
            self.assertTrue(mock_thread.called)

    def test_send_monitor_msg_to_ovsdb_connection(self):
        fake_ip = 'fake_ip'
        self.l2gw_ovsdb_conn.ovsdb_fd_states = {fake_ip: 'fake_status'}
        self.l2gw_ovsdb_conn.mgr.l2gw_agent_type = n_const.MONITOR
        self.l2gw_ovsdb_conn.ovsdb_conn_list = [fake_ip]
        with mock.patch.object(eventlet.greenthread, 'spawn_n') as (
                mock_thread):
            self.l2gw_ovsdb_conn._send_monitor_msg_to_ovsdb_connection(
                fake_ip)
            self.assertTrue(mock_thread.called)

    def test_exception_for_send_monitor_msg_to_ovsdb_connection(self):
        fake_ip = 'fake_ip'
        self.l2gw_ovsdb_conn.ovsdb_fd_states = {fake_ip: 'fake_status'}
        self.l2gw_ovsdb_conn.mgr.l2gw_agent_type = n_const.MONITOR
        self.l2gw_ovsdb_conn.ovsdb_conn_list = [fake_ip]
        with mock.patch.object(eventlet.greenthread, 'spawn_n',
                               side_effect=Exception) as mock_thread, \
                mock.patch.object(base_connection.LOG, 'warning') as mock_warning, \
                mock.patch.object(self.l2gw_ovsdb_conn,
                                  'disconnect') as mock_disconnect:
            self.l2gw_ovsdb_conn._send_monitor_msg_to_ovsdb_connection(
                fake_ip)
            self.assertTrue(mock_thread.called)
            self.assertTrue(mock_warning.called)
            mock_disconnect.assert_called_with(fake_ip)

    def test_echo_response(self):
        fake_resp = {"method": "echo",
                     "params": "fake_params",
                     "id": "fake_id",
                     }
        with mock.patch.object(eventlet.greenthread, 'sleep') as fake_thread, \
                mock.patch.object(jsonutils, 'loads', return_value=fake_resp) as mock_loads, \
                mock.patch.object(self.fakesocket,
                                  'recv',
                                  return_value=fake_resp) as mock_sock_rcv, \
                mock.patch.object(self.fakesocket,
                                  'send') as mock_sock_send:
            self.l2gw_ovsdb_conn._echo_response(self.fake_ip)
            self.assertTrue(fake_thread.called)
            self.assertTrue(mock_sock_rcv.called)
            mock_loads.assert_called_with(fake_resp)
            self.assertTrue(self.l2gw_ovsdb_conn.check_c_sock)
            self.assertTrue(mock_sock_send.called)

    def test_common_sock_rcv_thread_none(self):
        with mock.patch.object(base_connection.BaseConnection,
                               '_echo_response') as mock_resp, \
                mock.patch.object(eventlet.greenthread, 'sleep') as green_thrd_sleep, \
                mock.patch.object(self.fakesocket,
                                  'recv', return_value=None) as mock_rcv, \
                mock.patch.object(base_connection.BaseConnection,
                                  'disconnect') as mock_disconnect:
            self.l2gw_ovsdb_conn.check_c_sock = True
            self.l2gw_ovsdb_conn.read_on = True
            self.l2gw_ovsdb_conn._common_sock_rcv_thread(self.fake_ip)
            self.assertTrue(mock_resp.called)
            self.assertTrue(green_thrd_sleep.called)
            self.assertTrue(mock_rcv.called)
            self.assertTrue(mock_disconnect.called)
            self.assertFalse(self.l2gw_ovsdb_conn.connected)
            self.assertFalse(self.l2gw_ovsdb_conn.read_on)

    def test_disconnect_with_enable_manager(self):
        fake_ip = 'fake_ip'
        self.l2gw_ovsdb_conn.ovsdb_fd_states = {fake_ip: 'fake_status'}
        self.l2gw_ovsdb_conn.ovsdb_conn_list = [fake_ip]
        with mock.patch.object(self.fakesocket,
                               'close') as (mock_close):
            self.l2gw_ovsdb_conn.disconnect(fake_ip)
            self.assertTrue(mock_close.called)
            self.assertNotIn(fake_ip, self.l2gw_ovsdb_conn.ovsdb_fd_states)
            self.assertNotIn(fake_ip, self.l2gw_ovsdb_conn.ovsdb_conn_list)

    def test_get_ovsdb_ip_mapping(self):
        expected_ovsdb_ip_mapping = {'10.10.10.10': 'ovsdb1'}
        cfg.CONF.set_override('ovsdb_hosts',
                              'ovsdb1:10.10.10.10:6632',
                              'ovsdb')
        return_mapping = self.l2gw_ovsdb_conn._get_ovsdb_ip_mapping()
        self.assertEqual(expected_ovsdb_ip_mapping, return_mapping)

    def test_is_ssl_configured(self):
        self.l2gw_ovsdb_conn.ip_ovsdb_mapping = {'10.10.10.10': 'ovsdb1'}
        cfg.CONF.set_override('l2_gw_agent_priv_key_base_path',
                              '/home',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_cert_base_path',
                              '/home',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_ca_cert_base_path',
                              '/home',
                              'ovsdb')
        with mock.patch.object(os.path, 'isfile', return_value=True) as mock_isfile, \
                mock.patch.object(base_connection.LOG, 'error') as mock_error, \
                mock.patch.object(ssl, 'wrap_socket') as mock_wrap_sock:
            self.l2gw_ovsdb_conn._is_ssl_configured('10.10.10.10',
                                                    self.mock_sock)
            self.assertTrue(mock_isfile.called)
            self.assertTrue(mock_wrap_sock.called)
            self.assertFalse(mock_error.called)
            mock_wrap_sock.assert_called_with(
                self.mock_sock,
                server_side=True,
                keyfile='/home/ovsdb1.key',
                certfile='/home/ovsdb1.cert',
                ssl_version=ssl.PROTOCOL_SSLv23,
                ca_certs='/home/ovsdb1.ca_cert')

    def test_is_ssl_configured_for_certs_not_found(self):
        self.l2gw_ovsdb_conn.ip_ovsdb_mapping = {'10.10.10.10': 'ovsdb1'}
        cfg.CONF.set_override('l2_gw_agent_priv_key_base_path',
                              '/home/',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_cert_base_path',
                              '/home/',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_ca_cert_base_path',
                              '/home/',
                              'ovsdb')
        with mock.patch.object(os.path, 'isfile', return_value=False) as mock_isfile, \
                mock.patch.object(base_connection.LOG, 'error') as mock_error, \
                mock.patch.object(ssl, 'wrap_socket') as mock_wrap_sock:
            self.l2gw_ovsdb_conn._is_ssl_configured('10.10.10.10',
                                                    self.mock_sock)
            self.assertTrue(mock_isfile.called)
            self.assertFalse(mock_wrap_sock.called)
            self.assertTrue(mock_error.called)
