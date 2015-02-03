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

import contextlib

import eventlet
import mock

import ssl

from networking_l2gw.services.l2gateway.agent import l2gateway_config as conf
from networking_l2gw.services.l2gateway.agent.ovsdb import connection
from networking_l2gw.services.l2gateway.common import constants as n_const

from neutron.openstack.common import log as logging
from neutron.tests import base

LOG = logging.getLogger(__name__)


class TestOVSDBConnection(base.BaseTestCase):
    def setUp(self):
        super(TestOVSDBConnection, self).setUp()

        self.conf = mock.patch.object(conf, 'L2GatewayConfig').start()
        self.sock = mock.patch('socket.socket').start()
        self.ssl_sock = mock.patch.object(ssl, 'wrap_socket').start()
        self.plugin_rpc = mock.Mock()
        self.greenthread = mock.patch.object(eventlet.greenthread,
                                             'spawn_n').start()
        self.l2gw_ovsdb = connection.OVSDBConnection(mock.Mock(),
                                                     self.conf, True,
                                                     self.plugin_rpc)
        self.l2gw_ovsdb.socket = self.sock
        self.op_id = 'abcd'
        props = {'select': {'initial': True,
                            'insert': True,
                            'delete': True,
                            'modify': True}}
        self.monitor_message = {'id': self.op_id,
                                'method': 'monitor',
                                'params': [n_const.OVSDB_SCHEMA_NAME,
                                           None,
                                           {'Logical_Switch': [props],
                                            'Physical_Switch': [props],
                                            'Physical_Port': [props],
                                            'Ucast_Macs_Local': [props],
                                            'Ucast_Macs_Remote': [props],
                                            'Physical_Locator': [props],
                                            'Mcast_Macs_Local': [props],
                                            'Physical_Locator_Set': [props]}]}

        fake_message = {'Logical_Switch': props,
                        'Physical_Switch': props,
                        'Physical_Port': props,
                        'Ucast_Macs_Local': props,
                        'Ucast_Macs_Remote': props,
                        'Physical_Locator': props,
                        'Mcast_Macs_Local': props,
                        'Physical_Locator_Set': props}

        self.msg = self.monitor_message
        self.msg1 = {'result': fake_message}
        self.msg2 = {'method': 'update',
                     'params': ['', fake_message]}
        self.l2gw_ovsdb.responses = [self.monitor_message]

    def test_init(self):
        """Test case to test __init__."""
        with contextlib.nested(
            mock.patch.object(connection.LOG, 'debug'),
            mock.patch.object(eventlet.greenthread, 'spawn_n')
            ) as(logger_call, gt):
            self.l2gw_ovsdb.__init__(mock.Mock(), self.conf, self.plugin_rpc)
            self.assertTrue(self.l2gw_ovsdb.connected)
            self.assertTrue(logger_call.called)
            self.assertTrue(gt.called)
            self.assertTrue(self.sock.called)

    def test_set_monitor_response_handler(self):
        """Test case to test _set_monitor_response_handler with error_msg."""
        self.l2gw_ovsdb.connected = True
        with mock.patch.object(connection.OVSDBConnection,
                               'send', return_value=True) as send:
            self.l2gw_ovsdb.set_monitor_response_handler()
            self.assertTrue(send.called)

    def test_set_monitor_response_handler_with_error_in_send(self):
        """Test case to test _set_monitor_response_handler."""
        self.l2gw_ovsdb.connected = True
        with mock.patch.object(connection.OVSDBConnection,
                               'send', return_value=False) as send:
            self.l2gw_ovsdb.set_monitor_response_handler()
            self.assertTrue(send.called)

    def test_send(self):
        """Test case to test send."""
        with mock.patch.object(self.l2gw_ovsdb.socket, 'send',
                               side_effect=Exception) as send:
            with mock.patch.object(connection.LOG,
                                   'exception') as logger_call:
                self.l2gw_ovsdb.send(mock.Mock())
                self.assertTrue(send.called)
                self.assertTrue(logger_call.called)

    def test_disconnect(self):
        """Test case to test disconnect socket."""
        with mock.patch.object(self.l2gw_ovsdb.socket, 'close') as sock_close:
            self.l2gw_ovsdb.disconnect()
            self.assertTrue(sock_close.called)

    def test_rcv_thread_none(self):
        """Test case to test _rcv_thread receives None from socket."""
        self.assertTrue(self.l2gw_ovsdb.read_on)
        with mock.patch.object(self.l2gw_ovsdb.socket,
                               'recv', return_value=None) as sock_recv:
            with mock.patch.object(self.l2gw_ovsdb.socket,
                                   'close') as sock_close:
                self.l2gw_ovsdb._rcv_thread()
                self.assertTrue(sock_recv.called)
                self.assertFalse(self.l2gw_ovsdb.connected)
                self.assertFalse(self.l2gw_ovsdb.read_on)
                self.assertTrue(sock_close.called)

    def test_rcv_thread_exception(self):
        """Test case to test _rcv_thread with exception."""
        with contextlib.nested(
            mock.patch.object(self.l2gw_ovsdb.socket, 'recv',
                              side_effect=Exception,
                              return_value=None),
            mock.patch.object(self.l2gw_ovsdb.socket,
                              'close'),
            mock.patch.object(connection.LOG,
                              'exception')
            ) as (sock_recv, sock_close, logger_call):
                self.l2gw_ovsdb._rcv_thread()
                logger_call.assertCalled()
                self.assertTrue(sock_recv.called)
                self.assertFalse(self.l2gw_ovsdb.connected)
                self.assertFalse(self.l2gw_ovsdb.read_on)
                self.assertTrue(sock_close.called)

    def test_process_monitor_msg(self):
        """Test case to test _process_monitor_msg."""
        with contextlib.nested(
            mock.patch.object(connection.OVSDBConnection,
                              '_process_physical_port'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_physical_switch'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_logical_switch'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_ucast_macs_local'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_physical_locator'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_ucast_macs_remote'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_mcast_macs_local'),
            mock.patch.object(connection.OVSDBConnection,
                              '_process_physical_locator_set')
                ) as(proc_phy_port,
                     proc_phy_switch, proc_logic_switch,
                     proc_ucast_mac, proc_phy_loc, proc_ucast_mac_remote,
                     proc_mcast_mac_local, proc_physical_locator_set):
            self.l2gw_ovsdb._process_monitor_msg(self.msg1)
            proc_phy_port.assert_called()
            proc_phy_switch.assert_called()
            proc_logic_switch.assert_called()
            proc_ucast_mac.assert_called()
            proc_phy_loc.assert_called()
            proc_ucast_mac_remote.assert_called()
            proc_mcast_mac_local.assert_called()
            proc_physical_locator_set.assert_called()
            self.plugin_rpc.update_ovsdb_changes.assert_called_with(
                mock.ANY)
