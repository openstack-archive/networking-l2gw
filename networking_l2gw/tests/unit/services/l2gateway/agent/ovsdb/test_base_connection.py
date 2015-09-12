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

import eventlet

import contextlib
import socket
import ssl
import time

import mock
from oslo_serialization import jsonutils

from neutron.tests import base

from networking_l2gw.services.l2gateway.agent import l2gateway_config as conf
from networking_l2gw.services.l2gateway.agent.ovsdb import base_connection
from networking_l2gw.services.l2gateway.common import config

from oslo_config import cfg
from oslo_log import log as logging

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
        with contextlib.nested(
            mock.patch.object(base_connection.LOG, 'debug'),
            mock.patch.object(socket, 'socket', return_value=fakesocket)
        ) as(logger_call, mock_sock):
            self.l2gw_ovsdb.__init__(mock.Mock(), self.conf)
            self.assertTrue(self.l2gw_ovsdb.connected)
            self.assertTrue(logger_call.called)
            self.assertTrue(self.sock.called)

    def test_init_with_socket_error(self):
        """Test case to test __init__ with socket error exception."""

        fakesocket = SocketClass(socket.error)
        with contextlib.nested(
            mock.patch.object(base_connection.LOG, 'exception'),
            mock.patch.object(base_connection.LOG, 'warning'),
            mock.patch.object(socket, 'socket', return_value=fakesocket),
            mock.patch.object(time, 'sleep')
            ) as(logger_exc, logger_warn,
                 sock_connect, mock_sleep):
            ovsdb_conf = FakeConf()
            self.assertRaises(socket.error, base_connection.BaseConnection,
                              cfg.CONF.ovsdb, ovsdb_conf)
            self.assertTrue(logger_warn.called)
            self.assertTrue(logger_exc.called)
            self.assertTrue(sock_connect.called)

    def test_init_with_timeout(self):
        """Test case to test __init__ with socket timeout exception."""

        fakesocket = SocketClass(socket.timeout)
        with contextlib.nested(
            mock.patch.object(base_connection.LOG, 'exception'),
            mock.patch.object(base_connection.LOG, 'warning'),
            mock.patch.object(socket, 'socket', return_value=fakesocket),
            mock.patch.object(time, 'sleep')
            ) as(logger_exc, logger_warn,
                 sock_connect, mock_sleep):
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
        self.l2gw_ovsdb_conn = base_connection.BaseConnection(mock.Mock(),
                                                              self.conf)
        self.mock_sock = mock.patch('socket.socket').start()
        self.l2gw_ovsdb_conn.s = mock.patch('socket.socket').start()
        self.fakesocket = SocketClass()
        self.fake_ip = 'fake_ip'
        self.l2gw_ovsdb_conn.ovsdb_dicts = {'fake_ip': self.fakesocket}

    def test_init_with_enable_manager(self):
        fake_dict = {}
        with mock.patch.object(eventlet.greenthread,
                               'spawn') as (mock_thread):
            self.l2gw_ovsdb_conn.__init__(mock.Mock(), self.conf)
            self.assertEqual(self.l2gw_ovsdb_conn.s, mock.ANY)
            self.assertFalse(self.l2gw_ovsdb_conn.check_sock_rcv)
            self.assertIsNone(self.l2gw_ovsdb_conn.check_c_sock)
            self.assertEqual(self.l2gw_ovsdb_conn.ovsdb_dicts, fake_dict)
            self.assertEqual(self.l2gw_ovsdb_conn.ovsdb_fd_states, fake_dict)
            self.assertTrue(mock_thread.called)

    def test_echo_response(self):
        fake_resp = {"method": "echo",
                     "params": "fake_params",
                     "id": "fake_id",
                     }
        with contextlib.nested(
            mock.patch.object(eventlet.greenthread, 'sleep'),
            mock.patch.object(jsonutils, 'loads', return_value=fake_resp),
            mock.patch.object(self.fakesocket,
                              'recv',
                              return_value=fake_resp),
            mock.patch.object(self.fakesocket,
                              'send')
            ) as (
                fake_thread, mock_loads,
                mock_sock_rcv,
                mock_sock_send):
            self.l2gw_ovsdb_conn._echo_response(self.fake_ip)
            self.assertTrue(fake_thread.called)
            self.assertTrue(mock_sock_rcv.called)
            mock_loads.assert_called_with(fake_resp)
            self.assertTrue(self.l2gw_ovsdb_conn.check_c_sock)
            self.assertTrue(mock_sock_send.called)

    def test_common_sock_rcv_thread_none(self):
        with contextlib.nested(
            mock.patch.object(base_connection.BaseConnection,
                              '_echo_response'),
            mock.patch.object(eventlet.greenthread, 'sleep'),
            mock.patch.object(self.fakesocket,
                              'recv', return_value=None),
            mock.patch.object(base_connection.BaseConnection,
                              'disconnect')) as (
                mock_resp, green_thrd_sleep,
                mock_rcv, mock_disconnect):
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
        with mock.patch.object(self.fakesocket,
                               'close') as (mock_close):
            self.l2gw_ovsdb_conn.disconnect(self.fake_ip)
            self.assertTrue(mock_close.called)
