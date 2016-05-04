# Copyright (c) 2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mock

from neutron.common import rpc as n_rpc
from neutron.tests import base

from networking_l2gw.services.l2gateway import exceptions as l2gw_exc
from networking_l2gw.services.l2gateway.service_drivers import agent_api

import oslo_messaging as messaging


class TestL2GatewayAgentApi(base.BaseTestCase):

    def setUp(self):
        self.client_mock_p = mock.patch.object(n_rpc, 'get_client')
        self.client_mock = self.client_mock_p.start()
        self.context = mock.ANY
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.plugin_rpc = agent_api.L2gatewayAgentApi(
            self.topic, self.host)
        super(TestL2GatewayAgentApi, self).setUp()

    def test_set_monitor_agent(self):
        cctxt = mock.Mock()
        fake_hostname = 'fake_hostname'
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.set_monitor_agent(
            self.context, fake_hostname)
        cctxt.cast.assert_called_with(
            self.context, 'set_monitor_agent',
            hostname=fake_hostname)

    def test_add_vif_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator = {}
        fake_mac_remote = {}
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.add_vif_to_gateway(
            self.context, fake_ovsdb_identifier, fake_logical_switch,
            fake_physical_locator, fake_mac_remote)
        cctxt.call.assert_called_with(
            self.context, 'add_vif_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            logical_switch_dict=fake_logical_switch,
            locator_dict=fake_physical_locator,
            mac_dict=fake_mac_remote)

    def test_update_vif_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_physical_locator = {}
        fake_mac_remote = {}
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_vif_to_gateway(
            self.context, fake_ovsdb_identifier,
            fake_physical_locator, fake_mac_remote)
        cctxt.call.assert_called_with(
            self.context, 'update_vif_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            locator_dict=fake_physical_locator,
            mac_dict=fake_mac_remote)

    def test_delete_vif_from_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_vif_from_gateway(self.context,
                                                mock.ANY,
                                                mock.ANY,
                                                mock.ANY)
        cctxt.call.assert_called_with(
            self.context, 'delete_vif_from_gateway',
            ovsdb_identifier=mock.ANY, logical_switch_uuid=mock.ANY,
            mac=mock.ANY)

    def test_delete_network(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_network(self.context, mock.ANY, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_network', ovsdb_identifier=mock.ANY,
            logical_switch_uuid=mock.ANY)

    def test_validate_request_op_method(self):
        self.assertRaises(l2gw_exc.InvalidMethod,
                          self.plugin_rpc._validate_request_op_method,
                          self.context,
                          'fake_op_method')

    def test_update_connection_to_gateway(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator_list = []
        fake_mac_dicts = [{}]
        fake_port_dicts = [{}]
        fake_op_method = 'DELETE'
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_connection_to_gateway(
            self.context, fake_ovsdb_identifier, fake_logical_switch,
            fake_physical_locator_list, fake_mac_dicts, fake_port_dicts,
            fake_op_method)
        cctxt.call.assert_called_with(
            self.context, 'update_connection_to_gateway',
            ovsdb_identifier=fake_ovsdb_identifier,
            logical_switch_dict=fake_logical_switch,
            locator_dicts=fake_physical_locator_list,
            mac_dicts=fake_mac_dicts,
            port_dicts=fake_port_dicts,
            op_method=fake_op_method)

    def test_update_connection_to_gateway_with_invalid_op_method(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator_list = []
        fake_mac_dicts = [{}]
        fake_port_dicts = [{}]
        fake_op_method = 'create_delete_op'
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.assertRaises(
            l2gw_exc.InvalidMethod,
            self.plugin_rpc.update_connection_to_gateway,
            self.context, fake_ovsdb_identifier, fake_logical_switch,
            fake_physical_locator_list, fake_mac_dicts, fake_port_dicts,
            fake_op_method)

    def test_update_connection_to_gateway_with_error(self):
        cctxt = mock.Mock()
        fake_ovsdb_identifier = 'fake_ovsdb_id'
        fake_logical_switch = {}
        fake_physical_locator_list = []
        fake_mac_dicts = [{}]
        fake_port_dicts = [{}]
        fake_op_method = 'CREATE'
        self.plugin_rpc.client.prepare.return_value = cctxt

        # Test with a timeout exception
        with mock.patch.object(cctxt,
                               'call',
                               side_effect=messaging.MessagingTimeout):
            self.assertRaises(
                l2gw_exc.OVSDBError,
                self.plugin_rpc.update_connection_to_gateway,
                self.context, fake_ovsdb_identifier, fake_logical_switch,
                fake_physical_locator_list, fake_mac_dicts, fake_port_dicts,
                fake_op_method)

        # Test with a remote exception
        with mock.patch.object(cctxt,
                               'call',
                               side_effect=Exception):
            self.assertRaises(
                l2gw_exc.OVSDBError,
                self.plugin_rpc.update_connection_to_gateway,
                self.context, fake_ovsdb_identifier, fake_logical_switch,
                fake_physical_locator_list, fake_mac_dicts, fake_port_dicts,
                fake_op_method)
