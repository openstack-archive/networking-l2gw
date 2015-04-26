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
from neutron.openstack.common import loopingcall
from neutron.tests import base

from oslo.config import cfg

from networking_l2gw.services.l2gateway.agent import agent_api
from networking_l2gw.services.l2gateway.agent import base_agent_manager
from networking_l2gw.services.l2gateway.agent import l2gateway_config
from networking_l2gw.services.l2gateway.agent.ovsdb import manager
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
        with mock.patch.object(ovsdb_monitor,
                               'OVSDBMonitor') as ovsdb_connection:
            with mock.patch.object(eventlet.greenthread,
                                   'spawn_n') as event_spawn:
                with mock.patch.object(manager.OVSDBManager,
                                       'agent_to_plugin_rpc'
                                       ) as call_back:
                    self.l2gw_agent_manager._connect_to_ovsdb_server()
                    self.assertTrue(event_spawn.called)
                    self.assertTrue(ovsdb_connection.called)
                    ovsdb_connection.assert_called_with(
                        self.conf.ovsdb, gateway, call_back)

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
            mock_disconnect_ovsdb_servers.assert_called()
            mock_stop_looping.assert_called()

    def test_set_monitor_agent_type_monitor(self):
        self.l2gw_agent_manager.conf.host = 'fake_host'
        with mock.patch.object(manager.OVSDBManager,
                               '_connect_to_ovsdb_server'
                               ) as mock_conn:
            self.l2gw_agent_manager.set_monitor_agent(self.context,
                                                      'fake_host')
            self.assertEqual(n_const.MONITOR,
                             self.l2gw_agent_manager.agent_state.
                             get('configurations')[n_const.L2GW_AGENT_TYPE])
            self.assertEqual(n_const.MONITOR,
                             self.l2gw_agent_manager.l2gw_agent_type)
            mock_conn.assert_called()
            self.mock_looping_call.start().assert_called()

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
                logger_call.assert_called_once()
                mock_del_ls.assert_not_called()

    def test_disconnection(self):
        self.l2gw_agent_manager.gateways = {}
        fake_ovsdb_identifier = 'fake_ovsdb_identifier'
        gateway = l2gateway_config.L2GatewayConfig(self.fake_config_json)
        self.l2gw_agent_manager.gateways[fake_ovsdb_identifier] = gateway
        with mock.patch.object(ovsdb_writer,
                               'OVSDBWriter') as ovsdb_connection:
            ovsdb_connection.return_value.connected = True
            with mock.patch.object(ovsdb_writer.OVSDBWriter,
                                   'disconnect') as mock_dis:
                with self.l2gw_agent_manager._open_connection(
                        fake_ovsdb_identifier):
                    self.assertTrue(ovsdb_connection.called)
                    mock_dis.assert_called_once()

    def test_add_vif_to_gateway(self):
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_open_connection'),
            mock.patch.object(manager.OVSDBManager,
                              '_is_valid_request',
                              return_value=True),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'insert_ucast_macs_remote'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'disconnect')
        ) as (gw_open_conn, valid_req, ins_ucast, discon):
                self.l2gw_agent_manager.add_vif_to_gateway(
                    self.context, mock.Mock(), mock.Mock(),
                    mock.Mock(), mock.Mock())
                self.assertTrue(gw_open_conn.called)
                mocked_conn = gw_open_conn.return_value
                mocked_conn.insert_ucast_macs_remote.assert_called_once()
                discon.assert_called_once()

    def test_delete_vif_from_gateway(self):
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_open_connection'),
            mock.patch.object(manager.OVSDBManager,
                              '_is_valid_request',
                              return_value=True),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'delete_ucast_macs_remote'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'disconnect')
        ) as (gw_open_conn, valid_req, del_ucast, discon):
                self.l2gw_agent_manager.delete_vif_from_gateway(
                    self.context, mock.Mock(), mock.Mock(), mock.Mock())
                self.assertTrue(gw_open_conn.called)
                mocked_conn = gw_open_conn.return_value
                mocked_conn.delete_ucast_macs_remote.assert_called_once()
                discon.assert_called_once()

    def test_update_vif_to_gateway(self):
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_open_connection'),
            mock.patch.object(manager.OVSDBManager,
                              '_is_valid_request',
                              return_value=True),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'update_ucast_macs_remote'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'disconnect')
        ) as (gw_open_conn, valid_req, ins_ucast, discon):
                self.l2gw_agent_manager.update_vif_to_gateway(
                    self.context, mock.Mock(), mock.Mock(), mock.Mock())
                self.assertTrue(gw_open_conn.called)
                mocked_conn = gw_open_conn.return_value
                mocked_conn.update_ucast_macs_remote.assert_called_once()
                discon.assert_called_once()

    def test_update_connection_to_gateway(self):
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_open_connection'),
            mock.patch.object(manager.OVSDBManager,
                              '_is_valid_request',
                              return_value=True),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'update_connection_to_gateway'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'disconnect')
        ) as (gw_open_conn, valid_req, upd_con, discon):
                self.l2gw_agent_manager.update_connection_to_gateway(
                    self.context, mock.Mock(), mock.Mock(), mock.Mock(),
                    mock.Mock(), mock.Mock())
                self.assertTrue(gw_open_conn.called)
                mocked_conn = gw_open_conn.return_value
                mocked_conn.update_connection_to_gateway.assert_called_once()
                discon.assert_called_once()

    def test_delete_network(self):
        with contextlib.nested(
            mock.patch.object(manager.OVSDBManager,
                              '_open_connection'),
            mock.patch.object(manager.OVSDBManager,
                              '_is_valid_request',
                              return_value=True),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'delete_logical_switch'),
            mock.patch.object(ovsdb_writer.OVSDBWriter,
                              'disconnect')
        ) as (gw_open_conn, valid_req, del_ls, discon):
                self.l2gw_agent_manager.delete_network(
                    self.context, mock.Mock(), mock.Mock())
                self.assertTrue(gw_open_conn.called)
                mocked_conn = gw_open_conn.return_value
                mocked_conn.delete_logical_switch.assert_called_once()
                discon.assert_called_once()
