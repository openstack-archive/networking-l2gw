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
import socket

import eventlet
import mock

from neutron.agent.common import config as agent_config
from neutron.agent import rpc as agent_rpc
from neutron.common import rpc
from neutron import context
from neutron.tests import base

from oslo_config import cfg
from oslo_service import loopingcall

from networking_l2gw.services.l2gateway.agent import agent_api
from networking_l2gw.services.l2gateway.agent import base_agent_manager
from networking_l2gw.services.l2gateway.agent import l2gateway_config
from networking_l2gw.services.l2gateway.agent.ovsdb import manager
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_common_class
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_monitor
from networking_l2gw.services.l2gateway.agent.ovsdb import ovsdb_writer
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants as n_const


class TestManager(base.BaseTestCase):

    def setUp(self):
        super(TestManager, self).setUp()
        self.conf = cfg.CONF
        config.register_ovsdb_opts_helper(self.conf)
        agent_config.register_agent_state_opts_helper(self.conf)
        self.driver_mock = mock.Mock()
        self.fake_record_dict = {n_const.OVSDB_IDENTIFIER: 'fake_ovsdb_id'}
        cfg.CONF.set_override('report_interval', 1, 'AGENT')
        self.plugin_rpc = mock.patch.object(agent_api,
                                            'L2GatewayAgentApi').start()
        self.context = mock.Mock
        self.cntxt = mock.patch.object(context,
                                       'get_admin_context_without_session'
                                       ).start()
        self.test_rpc = mock.patch.object(rpc, 'get_client').start()
        self.mock_looping_call = mock.patch.object(loopingcall,
                                                   'FixedIntervalLoopingCall'
                                                   ).start()
        self.l2gw_agent_manager = manager.OVSDBManager(
            self.conf)
        self.l2gw_agent_manager.plugin_rpc = self.plugin_rpc
        self.fake_config_json = {n_const.OVSDB_IDENTIFIER:
                                 'fake_ovsdb_identifier',
                                 'ovsdb_ip': '5.5.5.5',
                                 'ovsdb_port': '6672',
                                 'private_key': 'dummy_key',
                                 'enable_ssl': False,
                                 'certificate': 'dummy_cert',
                                 'ca_cert': 'dummy_ca'}

    def test_extract_ovsdb_config(self):
        fake_ovsdb_config = {n_const.OVSDB_IDENTIFIER: 'host2',
                             'ovsdb_ip': '10.10.10.10',
                             'ovsdb_port': '6632',
                             'private_key': '/home/someuser/fakedir/host2.key',
                             'use_ssl': True,
                             'certificate':
                             '/home/someuser/fakedir/host2.cert',
                             'ca_cert': '/home/someuser/fakedir/host2.ca_cert'}
        cfg.CONF.set_override('ovsdb_hosts',
                              'host2:10.10.10.10:6632',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_priv_key_base_path',
                              '/home/someuser/fakedir',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_cert_base_path',
                              '/home/someuser/fakedir',
                              'ovsdb')
        cfg.CONF.set_override('l2_gw_agent_ca_cert_base_path',
                              '/home/someuser/fakedir',
                              'ovsdb')
        self.l2gw_agent_manager._extract_ovsdb_config(cfg.CONF)
        l2gwconfig = l2gateway_config.L2GatewayConfig(fake_ovsdb_config)
        gw = self.l2gw_agent_manager.gateways.get(
            fake_ovsdb_config[n_const.OVSDB_IDENTIFIER])
        self.assertEqual(l2gwconfig.ovsdb_identifier, gw.ovsdb_identifier)
        self.assertEqual(l2gwconfig.use_ssl, gw.use_ssl)
        self.assertEqual(l2gwconfig.ovsdb_ip, gw.ovsdb_ip)
        self.assertEqual(l2gwconfig.ovsdb_port, gw.ovsdb_port)
        self.assertEqual(l2gwconfig.private_key, gw.private_key)
        self.assertEqual(l2gwconfig.certificate, gw.certificate)
        self.assertEqual(l2gwconfig.ca_cert, gw.ca_cert)
        cfg.CONF.set_override('max_connection_retries',
                              25,
                              'ovsdb')
        self.assertRaises(SystemExit,
                          self.l2gw_agent_manager.
                          _extract_ovsdb_config,
                          cfg.CONF)

    def test_connect_to_ovsdb_server(self):
        self.l2gw_agent_manager.gateways = {}
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        ovsdb_ident = self.fake_config_json.get(n_const.OVSDB_IDENTIFIER)
        self.l2gw_agent_manager.gateways[ovsdb_ident] = gateway
        with contextlib.nested(
            mock.patch.object(ovsdb_monitor,
                              'OVSDBMonitor'),
            mock.patch.object(eventlet.greenthread,
                              'spawn_n'),
            mock.patch.object(manager.OVSDBManager,
                              'agent_to_plugin_rpc'),
            mock.patch.object(self.plugin_rpc,
                              'notify_ovsdb_states')
        ) as (ovsdb_connection, event_spawn, call_back, notify):
            self.l2gw_agent_manager._connect_to_ovsdb_server()
            self.assertTrue(event_spawn.called)
            self.assertTrue(ovsdb_connection.called)
            ovsdb_connection.assert_called_with(
                self.conf.ovsdb, gateway, call_back)
            notify.assert_called_once_with(mock.ANY, mock.ANY)

    def test_connect_to_ovsdb_server_with_exc(self):
        self.l2gw_agent_manager.gateways = {}
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        ovsdb_ident = self.fake_config_json.get(n_const.OVSDB_IDENTIFIER)
        self.l2gw_agent_manager.gateways[ovsdb_ident] = gateway
        with contextlib.nested(
            mock.patch.object(ovsdb_monitor.OVSDBMonitor,
                              '__init__',
                              side_effect=socket.error
                              ),
            mock.patch.object(eventlet.greenthread,
                              'spawn_n'),
            mock.patch.object(manager.LOG, 'error')
        ) as (ovsdb_connection, event_spawn, mock_warn):
                self.l2gw_agent_manager._connect_to_ovsdb_server()
                event_spawn.assert_not_called()

    def test_handle_report_state_failure(self):
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with contextlib.nested(
            mock.patch.object(self.l2gw_agent_manager,
                              '_disconnect_all_ovsdb_servers'
                              ),
            mock.patch.object(agent_rpc.PluginReportStateAPI,
                              'report_state',
                              side_effect=Exception),
            mock.patch.object(base_agent_manager.LOG,
                              'exception'),
            mock.patch.object(self.l2gw_agent_manager,
                              '_stop_looping_task')
        ) as (mock_disconnect_ovsdb_servers, mock_report_state,
              mock_log, mock_stop_looping):
            self.l2gw_agent_manager._report_state()
            self.assertEqual(self.l2gw_agent_manager.l2gw_agent_type,
                             '')
            self.assertEqual(self.l2gw_agent_manager.
                             agent_state.get('configurations'
                                             )[n_const.L2GW_AGENT_TYPE
                                               ],
                             '')
            self.assertTrue(mock_disconnect_ovsdb_servers.called)
            self.assertTrue(mock_stop_looping.called)

    def test_is_valid_request_fails(self):
        self.l2gw_agent_manager.gateways = {}
        fake_ovsdb_identifier = 'fake_ovsdb_identifier_2'
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        self.l2gw_agent_manager.gateways['fake_ovsdb_identifier'] = gateway
        with mock.patch.object(manager.LOG,
                               'warning') as logger_call:
            self.l2gw_agent_manager._is_valid_request(
                fake_ovsdb_identifier)
            self.assertEqual(1, logger_call.call_count)

    def test_open_connection(self):
        self.l2gw_agent_manager.gateways = {}
        fake_ovsdb_identifier = 'fake_ovsdb_identifier'
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        self.l2gw_agent_manager.gateways['fake_ovsdb_identifier'] = gateway
        with mock.patch.object(manager.LOG,
                               'warning') as logger_call:
            with mock.patch.object(ovsdb_writer,
                                   'OVSDBWriter') as ovsdb_connection:
                is_valid_request = self.l2gw_agent_manager._is_valid_request(
                    fake_ovsdb_identifier)
                with self.l2gw_agent_manager._open_connection(
                        fake_ovsdb_identifier):
                    self.assertTrue(is_valid_request)
                    self.assertEqual(0, logger_call.call_count)
                    self.assertTrue(ovsdb_connection.called)

    def test_open_connection_with_socket_error(self):
        self.l2gw_agent_manager.gateways = {}
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        self.l2gw_agent_manager.gateways['fake_ovsdb_identifier'] = gateway
        with contextlib.nested(
            mock.patch.object(manager.LOG, 'warning'),
            mock.patch.object(socket.socket, 'connect'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'delete_logical_switch')
        ) as (logger_call, mock_connect, mock_del_ls):
                mock_connect.side_effect = socket.error
                self.l2gw_agent_manager.delete_network(self.context,
                                                       mock.Mock(),
                                                       mock.Mock())
                self.assertEqual(1, logger_call.call_count)
                self.assertFalse(mock_del_ls.called)

    def test_init_with_enable_manager(self):
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection'),
            mock.patch.object(loopingcall, 'FixedIntervalLoopingCall')) as (
                mock_sock_open_conn, mock_loop):
            self.l2gw_agent_manager.__init__()
            self.assertTrue(mock_sock_open_conn.called)
            self.assertTrue(mock_loop.called)

    def test_sock_open_connection(self):
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.__init__()
            self.l2gw_agent_manager._sock_open_connection()
            self.assertTrue(mock_ovsdb_common.called)

    def test_set_monitor_agent_with_ovsdb_fd_None(self):
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.conf.host = 'fake_host'
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        self.l2gw_agent_manager.ovsdb_fd = None
        with mock.patch.object(manager.OVSDBManager,
                               '_sock_open_connection') as mock_open_conn:
            self.l2gw_agent_manager.set_monitor_agent(self.context,
                                                      'fake_host')
            self.assertTrue(mock_open_conn.called)

    def test_set_monitor_agent_with_ovsdb_fd_not_None(self):
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.conf.host = 'fake_host'
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class,
                              'OVSDB_commom_class'),
            mock.patch.object(eventlet.greenthread,
                              'spawn_n'),
            mock.patch.object(self.l2gw_agent_manager,
                              '_start_looping_task_ovsdb_states')) as (
                mock_ovsdb_common, mock_thread, mock_looping):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_monitor_table_thread = False
            self.l2gw_agent_manager.ovsdb_fd.check_sock_rcv = True
            self.l2gw_agent_manager.ovsdb_fd.ovsdb_dicts = {
                "fake_ip": "fake_sock"}
            self.l2gw_agent_manager.set_monitor_agent(self.context,
                                                      'fake_host')
            self.assertTrue(mock_thread.called)
            self.assertTrue(mock_looping.called)

    def test_update_connection_to_gateway_for_monitor_agent(self):
        """Test case to test update_connection_to_gateway for

        monitor agent with enable_manager.
        """
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.update_connection_to_gateway(
                self.context, mock.Mock(), mock.Mock(), mock.Mock(),
                mock.Mock(), mock.Mock())
            (self.l2gw_agent_manager.ovsdb_fd.update_connection_to_gateway.
             assert_called_with(mock.ANY, mock.ANY, mock.ANY, mock.ANY,
                                mock.ANY, False))

    def test_update_connection_to_gateway_for_transact_agent(self):
        """Test case to test update_connection_to_gateway

        with enable_manager.
        """
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = ''
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class, 'OVSDB_commom_class'),
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection')) as (
                mock_ovsdb_common, mock_open_conn):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_c_sock = True
            self.l2gw_agent_manager.update_connection_to_gateway(
                self.context, mock.Mock(), mock.Mock(), mock.Mock(),
                mock.Mock(), mock.Mock())
            (self.l2gw_agent_manager.ovsdb_fd._echo_response.
             assert_called_with(mock.ANY))
            self.assertTrue(mock_open_conn.called)
            (self.l2gw_agent_manager.ovsdb_fd.update_connection_to_gateway.
             assert_called_with(mock.ANY, mock.ANY, mock.ANY, mock.ANY,
                                mock.ANY))

    def test_delete_network_for_monitor_agent(self):
        """Test case to test delete_network with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.delete_network(
                self.context, mock.Mock(), "fake_logical_switch_uuid")
            (self.l2gw_agent_manager.ovsdb_fd.delete_logical_switch.
             assert_called_with("fake_logical_switch_uuid", mock.ANY, False))

    def test_delete_network_for_transact_agent(self):
        """Test case to test delete_network with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = ''
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class, 'OVSDB_commom_class'),
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection')) as (
                mock_ovsdb_common, mock_open_conn):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_c_sock = True
            self.l2gw_agent_manager.delete_network(
                self.context, mock.Mock(), "fake_logical_switch_uuid")
            (self.l2gw_agent_manager.ovsdb_fd._echo_response.
             assert_called_with(mock.ANY))
            self.assertTrue(mock_open_conn.called)
            (self.l2gw_agent_manager.ovsdb_fd.delete_logical_switch.
             assert_called_with("fake_logical_switch_uuid", mock.ANY, False))

    def test_add_vif_to_gateway_for_monitor_agent(self):
        """Test case to test add_vif_to_gateway with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.add_vif_to_gateway(
                self.context, mock.Mock(), "fake_logical_switch_dict",
                "fake_locator_dict", "fake_mac_dict")
            (self.l2gw_agent_manager.ovsdb_fd.insert_ucast_macs_remote.
             assert_called_with("fake_logical_switch_dict",
                                "fake_locator_dict", "fake_mac_dict",
                                mock.ANY, False))

    def test_add_vif_to_gateway_for_transact_agent(self):
        """Test case to test add_vif_to_gateway with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = ''
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class, 'OVSDB_commom_class'),
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection')) as (
                mock_ovsdb_common, mock_open_conn):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_c_sock = True
            self.l2gw_agent_manager.add_vif_to_gateway(
                self.context, mock.Mock(), "fake_logical_switch_dict",
                "fake_locator_dict", "fake_mac_dict")
            (self.l2gw_agent_manager.ovsdb_fd._echo_response.
             assert_called_with(mock.ANY))
            self.assertTrue(mock_open_conn.called)
            (self.l2gw_agent_manager.ovsdb_fd.insert_ucast_macs_remote.
             assert_called_with("fake_logical_switch_dict",
                                "fake_locator_dict", "fake_mac_dict",
                                mock.ANY))

    def test_delete_vif_from_gateway_for_monitor_agent(self):
        """Test case to test delete_vif_to_gateway with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.delete_vif_from_gateway(
                self.context, mock.Mock(), "fake_logical_switch_uuid",
                "fake_mac")
            (self.l2gw_agent_manager.ovsdb_fd.delete_ucast_macs_remote.
             assert_called_with("fake_logical_switch_uuid", "fake_mac",
                                mock.ANY, False))

    def test_delete_vif_to_gateway_for_transact_agent(self):
        """Test case to test delete_vif_to_gateway with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = ''
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class, 'OVSDB_commom_class'),
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection')) as (
                mock_ovsdb_common, mock_open_conn):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_c_sock = True
            self.l2gw_agent_manager.delete_vif_from_gateway(
                self.context, mock.Mock(), "fake_logical_switch_uuid",
                "fake_mac")
            (self.l2gw_agent_manager.ovsdb_fd._echo_response.
             assert_called_with(mock.ANY))
            self.assertTrue(mock_open_conn.called)
            (self.l2gw_agent_manager.ovsdb_fd.delete_ucast_macs_remote.
             assert_called_with("fake_logical_switch_uuid", "fake_mac",
                                mock.ANY))

    def test_update_vif_from_gateway_for_monitor_agent(self):
        """Test case to test update_vif_to_gateway with enable_manager."""
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = n_const.MONITOR
        with mock.patch.object(ovsdb_common_class,
                               'OVSDB_commom_class') as mock_ovsdb_common:
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.update_vif_to_gateway(
                self.context, mock.Mock(),
                "fake_logical_switch_uuid", "fake_mac")
            (self.l2gw_agent_manager.ovsdb_fd.update_ucast_macs_remote.
             assert_called_with(
                 "fake_logical_switch_uuid", "fake_mac", mock.ANY, False))

    def test_update_vif_to_gateway_for_transact_agent(self):
        """Test case to test update_vif_to_gateway

           with enable_manager.
        """
        cfg.CONF.set_override('enable_manager', True, 'ovsdb')
        self.l2gw_agent_manager.__init__()
        self.l2gw_agent_manager.l2gw_agent_type = ''
        with contextlib.nested(
            mock.patch.object(ovsdb_common_class, 'OVSDB_commom_class'),
            mock.patch.object(manager.OVSDBManager,
                              '_sock_open_connection')) as (
                mock_ovsdb_common, mock_open_conn):
            self.l2gw_agent_manager.ovsdb_fd = mock_ovsdb_common.return_value
            self.l2gw_agent_manager.ovsdb_fd.check_c_sock = True
            self.l2gw_agent_manager.update_vif_to_gateway(
                self.context, mock.Mock(), "fake_logical_switch_uuid",
                "fake_mac")
            (self.l2gw_agent_manager.ovsdb_fd._echo_response.
             assert_called_with(mock.ANY))
            self.assertTrue(mock_open_conn.called)
            (self.l2gw_agent_manager.ovsdb_fd.update_ucast_macs_remote.
             assert_called_with("fake_logical_switch_uuid", "fake_mac",
                                mock.ANY))
