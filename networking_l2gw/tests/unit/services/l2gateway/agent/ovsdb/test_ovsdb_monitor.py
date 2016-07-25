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

import socket
import ssl

import eventlet
import mock

from neutron.tests import base

from networking_l2gw.services.l2gateway.agent import l2gateway_config as conf
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_monitor
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions
from networking_l2gw.tests.unit.services.l2gateway.agent.ovsdb import (
    test_base_connection as base_test)

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

LOG = logging.getLogger(__name__)


class TestOVSDBMonitor(base.BaseTestCase):
    def setUp(self):
        super(TestOVSDBMonitor, self).setUp()

        self.conf = mock.patch.object(conf, 'L2GatewayConfig').start()
        config.register_ovsdb_opts_helper(cfg.CONF)
        self.callback = mock.Mock()
        cfg.CONF.set_override('max_connection_retries', 0, 'ovsdb')

        self.sock = mock.patch('socket.socket').start()
        self.ssl_sock = mock.patch.object(ssl, 'wrap_socket').start()
        self.greenthread = mock.patch.object(eventlet.greenthread,
                                             'spawn_n').start()
        self.l2gw_ovsdb = ovsdb_monitor.OVSDBMonitor(mock.Mock(),
                                                     self.conf,
                                                     self.callback)
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

        fakesocket = base_test.SocketClass()
        with mock.patch.object(ovsdb_monitor.LOG, 'debug'), \
                mock.patch.object(eventlet.greenthread, 'spawn') as gt, \
                mock.patch.object(socket, 'socket',
                                  return_value=fakesocket):
            self.l2gw_ovsdb.__init__(mock.Mock(), self.conf,
                                     self.callback)
            self.assertTrue(self.l2gw_ovsdb.connected)
            self.assertTrue(gt.called)
            self.assertTrue(self.sock.called)

    def test_setup_dispatch_table(self):
        expected_dict = {'Logical_Switch':
                         self.l2gw_ovsdb._process_logical_switch,
                         'Ucast_Macs_Local':
                         self.l2gw_ovsdb._process_ucast_macs_local,
                         'Physical_Locator':
                         self.l2gw_ovsdb._process_physical_locator,
                         'Ucast_Macs_Remote':
                         self.l2gw_ovsdb._process_ucast_macs_remote,
                         'Mcast_Macs_Local':
                         self.l2gw_ovsdb._process_mcast_macs_local,
                         'Physical_Locator_Set':
                         self.l2gw_ovsdb._process_physical_locator_set
                         }
        self.l2gw_ovsdb._setup_dispatch_table()
        self.assertEqual(expected_dict, self.l2gw_ovsdb.dispatch_table)

    def test_set_monitor_response_handler(self):
        """Test case to test _set_monitor_response_handler with error_msg."""
        self.l2gw_ovsdb.connected = True
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_set_handler') as set_handler, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  'send', return_value=True) as send, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_response',
                                  return_value=(mock.ANY, False)) as process_resp, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_monitor_msg') as process_monitor_msg, \
                mock.patch.object(ovsdb_monitor.LOG, 'warning'):
            self.l2gw_ovsdb.set_monitor_response_handler()
            self.assertTrue(set_handler.called)
            self.assertTrue(send.called)
            self.assertTrue(process_monitor_msg.called)
            self.assertTrue(process_resp.called)

    def test_set_monitor_response_handler_with_error_in_send(self):
        """Test case to test _set_monitor_response_handler."""
        self.l2gw_ovsdb.connected = True
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_set_handler') as set_handler, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  'send', return_value=False) as send, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_response',
                                  return_value=(mock.ANY, True)) as process_resp, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_monitor_msg') as process_monitor_msg, \
                mock.patch.object(ovsdb_monitor.LOG,
                                  'warning'):
            self.l2gw_ovsdb.set_monitor_response_handler()
            self.assertTrue(set_handler.called)
            self.assertTrue(send.called)
            self.assertFalse(process_resp.called)
            self.assertFalse(process_monitor_msg.called)

    def test_update_event_handler(self):
        """Test case to test _update_event_handler."""
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_process_update_event'
                               ) as process_update_event:
            self.l2gw_ovsdb._update_event_handler(self.msg, mock.ANY)
            process_update_event.assert_called_once_with(self.msg, mock.ANY)

    def test_process_update_event(self):
        """Test case to test _process_update_event."""
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_process_physical_port') as proc_phy_port, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_physical_switch') as proc_phy_switch, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_logical_switch') as proc_logic_switch, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_ucast_macs_local') as proc_ucast_mac, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_physical_locator') as proc_phy_loc, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_ucast_macs_remote') as proc_ucast_mac_remote, \
                mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                                  '_process_mcast_macs_local') as proc_mcast_mac_local, \
                mock.patch.object(
                    ovsdb_monitor.OVSDBMonitor,
                    '_process_physical_locator_set') as proc_phys_loc_set:
            self.l2gw_ovsdb._setup_dispatch_table()
            self.l2gw_ovsdb._process_update_event(self.msg2, mock.ANY)
            self.assertTrue(proc_phy_port.called)
            self.assertTrue(proc_phy_switch.called)
            self.assertTrue(proc_logic_switch.called)
            self.assertTrue(proc_ucast_mac.called)
            self.assertTrue(proc_phy_loc.called)
            self.assertTrue(proc_ucast_mac_remote.called)
            self.assertTrue(proc_mcast_mac_local.called)
            self.assertTrue(proc_phys_loc_set.called)
            self.assertTrue(self.callback.called)

    def test_process_response_raise_exception(self):
        """Test case to test _process_response with exception."""
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_response') as resp:
            with mock.patch.object(ovsdb_monitor.LOG, 'debug'):
                self.assertRaises(exceptions.OVSDBError,
                                  self.l2gw_ovsdb._process_response,
                                  self.op_id)
                resp.assert_called_once_with(self.op_id)

    def test_process_response(self):
        """Test case to test _process_response."""
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_response',
                               return_value={'key':
                                             'some_value'
                                             }) as resp:
            with mock.patch.object(ovsdb_monitor.LOG, 'debug'):
                self.l2gw_ovsdb._process_response(self.op_id)
                resp.assert_called_once_with(self.op_id)

    def test_default_echo_handler(self):
        """Test case to test _default_echo_handler."""
        dummy_msg = {'params': 'fake_params',
                     'id': 'fake_id'}
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               'send') as send:
            self.l2gw_ovsdb._default_echo_handler(dummy_msg, mock.ANY)
            self.assertTrue(send.called)

    def test_set_handler(self):
        """Test case to test _set_handler."""
        dummy_method = "dummy"
        dummy_handler = "handler"
        self.l2gw_ovsdb._set_handler(dummy_method, dummy_handler)
        self.assertEqual(self.l2gw_ovsdb.handlers[dummy_method],
                         dummy_handler)

    def test_on_remote_message(self):
        """Test case to test _on_remote_message."""
        self.l2gw_ovsdb.handlers = mock.Mock()
        with mock.patch.object(ovsdb_monitor.LOG, 'debug'):
            with mock.patch.object(jsonutils, 'loads') as json_load:
                self.l2gw_ovsdb._on_remote_message(self.msg)
                self.assertTrue(json_load.called)
                handler_method = json_load.return_value
                handler_method.get.assert_called_once_with(mock.ANY, mock.ANY)

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
        with mock.patch.object(self.l2gw_ovsdb.socket, 'recv',
                               side_effect=Exception,
                               return_value=None) as sock_recv, \
                mock.patch.object(self.l2gw_ovsdb.socket,
                                  'close') as sock_close, \
                mock.patch.object(ovsdb_monitor.LOG,
                                  'exception') as logger_call:
            self.l2gw_ovsdb._rcv_thread()
            self.assertTrue(logger_call.called)
            self.assertTrue(sock_recv.called)
            self.assertFalse(self.l2gw_ovsdb.connected)
            self.assertFalse(self.l2gw_ovsdb.read_on)
            self.assertTrue(sock_close.called)

    def test_form_ovsdb_data(self):
        some_value = mock.Mock()
        expect = {n_const.OVSDB_IDENTIFIER: self.conf.ovsdb_identifier,
                  'new_logical_switches': some_value,
                  'new_physical_switches': some_value,
                  'new_physical_ports': some_value,
                  'new_physical_locators': some_value,
                  'new_local_macs': some_value,
                  'new_remote_macs': some_value,
                  'new_mlocal_macs': some_value,
                  'new_locator_sets': some_value,
                  'deleted_logical_switches': some_value,
                  'deleted_physical_switches': some_value,
                  'deleted_physical_ports': some_value,
                  'deleted_physical_locators': some_value,
                  'deleted_local_macs': some_value,
                  'deleted_remote_macs': some_value,
                  'deleted_mlocal_macs': some_value,
                  'deleted_locator_sets': some_value,
                  'modified_logical_switches': some_value,
                  'modified_physical_switches': some_value,
                  'modified_physical_ports': some_value,
                  'modified_physical_locators': some_value,
                  'modified_local_macs': some_value,
                  'modified_remote_macs': some_value,
                  'modified_mlocal_macs': some_value,
                  'modified_locator_sets': some_value}
        with mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                               '_get_list',
                               return_value=some_value
                               ):
            result = self.l2gw_ovsdb._form_ovsdb_data(mock.Mock(), mock.ANY)
            self.assertEqual(expect, result)

    def test_process_physical_port(self):
        """Test case to process new physical_port."""
        fake_id = 'fake_id'
        add = {'new': {'uuid': 'fake_id',
                       'name': 'fake_name',
                       'physical_switch_id': 'fake_switch_id',
                       'port_fault_status': 'fake_status',
                       'vlan_bindings': [["some"], []]}}
        delete = {'old': {'uuid': 'fake_id_old',
                          'name': 'fake_name_old',
                          'physical_switch_id': 'fake_switch_id_old'}}
        modify = {}
        modify.update(add)
        modify.update(delete)
        port_map = {'fake_id': 'fake_switch_id'}
        data_dict = {'new_physical_ports': [],
                     'modified_physical_ports': [],
                     'deleted_physical_ports': []}

        with mock.patch.object(ovsdb_schema, 'PhysicalPort') as phy_port:
            with mock.patch.object(ovsdb_schema, 'VlanBinding'):
                # test add
                self.l2gw_ovsdb._process_physical_port(fake_id,
                                                       add,
                                                       port_map,
                                                       data_dict)
                phy_port.assert_called_once_with(
                    fake_id, 'fake_name', None, None, 'fake_status')
                self.assertIn(phy_port.return_value,
                              data_dict.get('new_physical_ports'))

                # test modify
                self.l2gw_ovsdb._process_physical_port(fake_id,
                                                       modify,
                                                       port_map,
                                                       data_dict)
                self.assertIn(phy_port.return_value,
                              data_dict.get('modified_physical_ports'))
                # test delete
                self.l2gw_ovsdb._process_physical_port(fake_id,
                                                       delete,
                                                       port_map,
                                                       data_dict)
                self.assertIn(phy_port.return_value,
                              data_dict.get('deleted_physical_ports'))

    def test_process_physical_port_with_empty_fault_status(self):
        """Test case to process new physical_port with empty fault status."""
        fake_id = 'fake_id'
        add = {'new': {'uuid': 'fake_id',
                       'name': 'fake_name',
                       'physical_switch_id': 'fake_switch_id',
                       'port_fault_status': ['set', []],
                       'vlan_bindings': [["some"], []]}}
        port_map = {'fake_id': 'fake_switch_id'}
        data_dict = {'new_physical_ports': [],
                     'modified_physical_ports': [],
                     'deleted_physical_ports': []}

        with mock.patch.object(ovsdb_schema, 'PhysicalPort') as phy_port:
            with mock.patch.object(ovsdb_schema, 'VlanBinding'):
                # test add
                self.l2gw_ovsdb._process_physical_port(fake_id,
                                                       add,
                                                       port_map,
                                                       data_dict)
                phy_port.assert_called_once_with(
                    fake_id, 'fake_name', None, None, None)
                self.assertIn(phy_port.return_value,
                              data_dict.get('new_physical_ports'))

    def test_process_physical_switch(self):
        """Test case to process new physical_switch."""
        port_map = {'fake_id': 'fake_switch_id'}
        with mock.patch.object(ovsdb_schema, 'PhysicalPort') as phy_port:
            with mock.patch.object(ovsdb_schema,
                                   'PhysicalSwitch') as phy_switch:
                physical_port = phy_port.return_value
                fake_id = 'fake_id'
                add = {'new': {'uuid': 'fake_id',
                               'name': 'fake_name',
                               'tunnel_ips': 'fake_tunnel_ip',
                               'switch_fault_status': 'fake_status',
                               'ports': ['set', 'set',
                                         physical_port]}}
                delete = {'old': {'uuid': 'fake_id_old',
                                  'name': 'fake_name_old',
                                  'tunnel_ips': 'fake_tunnel_ip_old',
                                  'ports': ['', physical_port]}}
                modify = {}
                modify.update(add)
                modify.update(delete)
                data_dict = {'new_physical_switches': [],
                             'modified_physical_switches': [],
                             'deleted_physical_switches': [],
                             'new_physical_ports': []}
                # test add
                self.l2gw_ovsdb._process_physical_switch(fake_id,
                                                         add,
                                                         port_map,
                                                         data_dict)
                self.assertIn(phy_switch.return_value,
                              data_dict['new_physical_switches'])
                phy_switch.assert_called_once_with(
                    'fake_id', 'fake_name',
                    'fake_tunnel_ip', 'fake_status')
                # test modify
                self.l2gw_ovsdb._process_physical_switch(fake_id,
                                                         modify,
                                                         port_map,
                                                         data_dict)
                self.assertIn(phy_switch.return_value,
                              data_dict['modified_physical_switches'])
                # test delete
                self.l2gw_ovsdb._process_physical_switch(fake_id,
                                                         delete,
                                                         port_map,
                                                         data_dict)
                self.assertIn(phy_switch.return_value,
                              data_dict['deleted_physical_switches'])

    def test_process_physical_switch_with_empty_fault_status(self):
        """Test case to process new physical_switch with empty fault status."""
        port_map = {'fake_id': 'fake_switch_id'}
        with mock.patch.object(ovsdb_schema, 'PhysicalPort') as phy_port:
            with mock.patch.object(ovsdb_schema,
                                   'PhysicalSwitch') as phy_switch:
                physical_port = phy_port.return_value
                fake_id = 'fake_id'
                add = {'new': {'uuid': 'fake_id',
                               'name': 'fake_name',
                               'tunnel_ips': 'fake_tunnel_ip',
                               'switch_fault_status': ['set', []],
                               'ports': ['set', 'set',
                                         physical_port]}}
                data_dict = {'new_physical_switches': [],
                             'modified_physical_switches': [],
                             'deleted_physical_switches': [],
                             'new_physical_ports': []}
                # test add
                self.l2gw_ovsdb._process_physical_switch(fake_id,
                                                         add,
                                                         port_map,
                                                         data_dict)
                self.assertIn(phy_switch.return_value,
                              data_dict['new_physical_switches'])
                phy_switch.assert_called_once_with('fake_id', 'fake_name',
                                                   'fake_tunnel_ip', None)

    def test_process_logical_switch(self):
        """Test case to process new logical_switch."""
        fake_id = 'fake_id'
        fake_name = 'fake_name'
        fake_tunnel_key = 'fake_tunnel_key'
        add = {'new': {'name': 'fake_name',
                       'tunnel_key': 'fake_tunnel_key'}}
        delete = {'old': {'name': 'fake_name_old',
                          'tunnel_key': 'fake_tunnel_key_old'}}
        modify = {}
        modify.update(add)
        modify.update(delete)
        data_dict = {'new_logical_switches': [],
                     'modified_logical_switches': [],
                     'deleted_logical_switches': []}

        with mock.patch.object(ovsdb_schema,
                               'LogicalSwitch') as logical_switch:
            # test add
            self.l2gw_ovsdb._process_logical_switch(fake_id, add,
                                                    data_dict)
            logical_switch.assert_called_once_with(
                fake_id, fake_name, fake_tunnel_key, None)
            self.assertIn(logical_switch.return_value,
                          data_dict['new_logical_switches'])

            # test modify
            self.l2gw_ovsdb._process_logical_switch(fake_id, modify,
                                                    data_dict)
            self.assertIn(logical_switch.return_value,
                          data_dict['modified_logical_switches'])

            # test delete
            self.l2gw_ovsdb._process_logical_switch(fake_id, delete,
                                                    data_dict)
            self.assertIn(logical_switch.return_value,
                          data_dict['deleted_logical_switches'])

    def test_process_ucast_macs_local(self):
        """Test case to process new ucast_macs_local."""
        fake_id = 'fake_id'
        add = {'new': {'locator': ["uuid", "fake_locator_id"],
                       'MAC': 'fake_mac',
                       'logical_switch':
                       ["uuid",
                        "fake_logical_switch_id"],
                       'ipaddr': 'fake_ip_address'}}
        delete = {'old': {'MAC': 'fake_mac_old',
                          'logical_switch':
                          ["uuid",
                           "fake_logical_switch_id_old"]}}
        modify = {}
        modify.update(add)
        modify.update(delete)
        fake_mac = 'fake_mac'
        fake_logical_switch_id = 'fake_logical_switch_id'
        fake_locator_id = 'fake_locator_id'
        fake_ip_address = 'fake_ip_address'
        data_dict = {'new_local_macs': [],
                     'modified_local_macs': [],
                     'deleted_local_macs': []}
        with mock.patch.object(ovsdb_schema,
                               'UcastMacsLocal') as ucast_mac_local:
            # test add
            self.l2gw_ovsdb._process_ucast_macs_local(fake_id, add,
                                                      data_dict)
            ucast_mac_local.assert_called_once_with(fake_id, fake_mac,
                                                    fake_logical_switch_id,
                                                    fake_locator_id,
                                                    fake_ip_address)
            self.assertIn(ucast_mac_local.return_value,
                          data_dict['new_local_macs'])

            # test modify
            self.l2gw_ovsdb._process_ucast_macs_local(fake_id, modify,
                                                      data_dict)
            self.assertIn(ucast_mac_local.return_value,
                          data_dict['modified_local_macs'])

            # test delete
            self.l2gw_ovsdb._process_ucast_macs_local(fake_id, delete,
                                                      data_dict)
            self.assertIn(ucast_mac_local.return_value,
                          data_dict['deleted_local_macs'])

    def test_process_ucast_macs_remote(self):
        """Test case to process new ucast_macs_remote."""
        fake_id = 'fake_id'
        add = {'new': {'locator': ["uuid", "fake_locator_id"],
                       'MAC': 'fake_mac',
                       'logical_switch':
                       ["uuid",
                        "fake_logical_switch_id"],
                       'ipaddr': 'fake_ip_address'}}
        delete = {'old': {'MAC': 'fake_mac_old',
                          'logical_switch':
                          ["uuid", "fake_logical_switch_id_old"]}}
        modify = {}
        modify.update(add)
        modify.update(delete)
        fake_mac = 'fake_mac'
        fake_logical_switch_id = 'fake_logical_switch_id'
        fake_locator_id = 'fake_locator_id'
        fake_ip_address = 'fake_ip_address'
        data_dict = {'new_remote_macs': [],
                     'modified_remote_macs': [],
                     'deleted_remote_macs': []}

        with mock.patch.object(ovsdb_schema,
                               'UcastMacsRemote') as ucast_mac_remote:
            # test add
            self.l2gw_ovsdb._process_ucast_macs_remote(fake_id,
                                                       add,
                                                       data_dict)
            ucast_mac_remote.assert_called_once_with(fake_id, fake_mac,
                                                     fake_logical_switch_id,
                                                     fake_locator_id,
                                                     fake_ip_address)
            self.assertIn(ucast_mac_remote.return_value,
                          data_dict['new_remote_macs'])
            # test modify
            self.l2gw_ovsdb._process_ucast_macs_remote(fake_id,
                                                       modify,
                                                       data_dict)
            self.assertIn(ucast_mac_remote.return_value,
                          data_dict['modified_remote_macs'])

            # test delete
            self.l2gw_ovsdb._process_ucast_macs_remote(fake_id,
                                                       delete,
                                                       data_dict)
            self.assertIn(ucast_mac_remote.return_value,
                          data_dict['deleted_remote_macs'])

    def test_process_physical_locator(self):
        """Test case to process new physical locator."""
        fake_id = 'fake_id'
        add = {'new': {"dst_ip": "fake_dst_ip"}}
        delete = {'old': {"dst_ip": "fake_dst_ip_old"}}
        modify = {}
        modify.update(add)
        modify.update(delete)
        data_dict = {'new_physical_locators': [],
                     'modified_physical_locators': [],
                     'deleted_physical_locators': []}

        fake_dst_ip = 'fake_dst_ip'
        with mock.patch.object(ovsdb_schema, 'PhysicalLocator') as phy_locator:
            # test add
            self.l2gw_ovsdb._process_physical_locator(fake_id, add,
                                                      data_dict)
            phy_locator.assert_called_once_with(fake_id, fake_dst_ip)
            self.assertIn(phy_locator.return_value,
                          data_dict['new_physical_locators'])
            # test delete
            self.l2gw_ovsdb._process_physical_locator(fake_id, delete,
                                                      data_dict)
            self.assertIn(phy_locator.return_value,
                          data_dict['deleted_physical_locators'])

            # test modify
            self.l2gw_ovsdb._process_physical_locator(fake_id, modify,
                                                      data_dict)
            self.assertIn(phy_locator.return_value,
                          data_dict['modified_physical_locators'])

    def test_process_mcast_macs_local(self):
        """Test case to process new mcast_macs_local."""
        fake_id = 'fake_id'
        add = {'new': {'locator_set': ["uuid", "fake_locator_id"],
                       'MAC': 'fake_mac',
                       'logical_switch': ["uuid",
                                          "fake_logical_switch_id"],
                       'ipaddr': 'fake_ip_address'}}
        delete = {'old': {'locator': ["uuid", "fake_locator_id"],
                          'MAC': 'fake_mac',
                          'logical_switch': ["uuid",
                                             "fake_logical_switch_id"],
                          'ipaddr': 'fake_ip_address'}}

        fake_mac = 'fake_mac'
        fake_logical_switch_id = 'fake_logical_switch_id'
        fake_locator_id = 'fake_locator_id'
        fake_ip_address = 'fake_ip_address'
        data_dict = {'new_mlocal_macs': [],
                     'deleted_mlocal_macs': []}
        with mock.patch.object(ovsdb_schema,
                               'McastMacsLocal') as mcast_mac_local:
            # test add
            self.l2gw_ovsdb._process_mcast_macs_local(fake_id,
                                                      add, data_dict)
            mcast_mac_local.assert_called_once_with(fake_id, fake_mac,
                                                    fake_logical_switch_id,
                                                    fake_locator_id,
                                                    fake_ip_address)
            self.assertIn(mcast_mac_local.return_value,
                          data_dict['new_mlocal_macs'])

            # test delete
            self.l2gw_ovsdb._process_mcast_macs_local(fake_id,
                                                      delete,
                                                      data_dict)
            self.assertTrue(mcast_mac_local.called)
            self.assertIn(mcast_mac_local.return_value,
                          data_dict['deleted_mlocal_macs'])

    def test_process_physical_locator_set(self):
        """Test case to process new physical_locaor_set."""
        fake_id = 'fake_id'
        add = {'new': {'locators': ["set", [["uuid", "fake_id1"],
                                            ["uuid", "fake_id2"]]]
                       }}
        delete = {'old': {'locators': ["set", [["uuid", "fake_id1"],
                                               ["uuid", "fake_id2"]]]
                          }}
        fake_locators = ["fake_id1", "fake_id2"]
        data_dict = {'new_locator_sets': [],
                     'deleted_locator_sets': []}
        with mock.patch.object(ovsdb_schema,
                               'PhysicalLocatorSet') as phys_loc_set:
            self.l2gw_ovsdb._process_physical_locator_set(fake_id,
                                                          add,
                                                          data_dict)
            phys_loc_set.assert_called_once_with(fake_id, fake_locators)
            PhysLocatorSet = phys_loc_set.return_value
            self.assertIn(PhysLocatorSet,
                          data_dict['new_locator_sets'])

            self.l2gw_ovsdb._process_physical_locator_set(fake_id,
                                                          delete,
                                                          data_dict)
            self.assertTrue(phys_loc_set.called)
            PhysLocatorSet = phys_loc_set.return_value
            self.assertIn(PhysLocatorSet,
                          data_dict['deleted_locator_sets'])


class SocketClass(object):
    def __init__(self,
                 connect_error=None,
                 send_error=None,
                 recv_error=None,
                 rcv_data=None,
                 sock=None,
                 ip_addr=None):
        self.connect_error = connect_error
        self.rcv_data = rcv_data
        self.send_error = send_error
        self.recv_error = recv_error
        self.sock = sock
        self.ip_addr = ip_addr

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

    def bind(self, host_port):
        pass

    def listen(self, conn):
        pass

    def accept(self):
        return self.sock, self.ip_addr

    def setsockopt(self, sock_opt, sock_reuse, mode):
        pass


class TestOVSDBMonitor_with_enable_manager(base.BaseTestCase):
    def setUp(self):
        super(TestOVSDBMonitor_with_enable_manager, self).setUp()
        config.register_ovsdb_opts_helper(cfg.CONF)
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.conf = mock.Mock()
        self.callback = mock.Mock()
        self.l2gw_ovsdb = ovsdb_monitor.OVSDBMonitor(mock.Mock(),
                                                     self.conf,
                                                     self.callback)

    def test_init_with_enable_manager(self):
        self.l2gw_ovsdb.__init__(mock.Mock(), self.conf,
                                 self.callback)
        self.assertTrue(self.l2gw_ovsdb.enable_manager)
        self.assertFalse(self.l2gw_ovsdb.check_monitor_table_thread)
