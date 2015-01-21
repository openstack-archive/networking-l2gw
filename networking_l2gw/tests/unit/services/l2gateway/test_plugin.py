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

from networking_l2gw.services.l2gateway import plugin as l2gw_plugin


class TestL2GatewayAgentApi(base.BaseTestCase):

    def setUp(self):
        self.client_mock_p = mock.patch.object(n_rpc, 'get_client')
        self.client_mock = self.client_mock_p.start()
        self.context = mock.ANY
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.plugin_rpc = l2gw_plugin.L2gatewayAgentApi(
            self.topic, self.context, self.host)
        super(TestL2GatewayAgentApi, self).setUp()

    def test_add_vif_to_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.add_vif_to_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'add_vif_to_gateway', record_dict=mock.ANY)

    def test_delete_vif_from_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_vif_from_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_vif_from_gateway', record_dict=mock.ANY)

    def test_delete_network(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_network(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_network', record_dict=mock.ANY)

    def test_update_connection_to_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_connection_to_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'update_connection_to_gateway',
            record_dict=mock.ANY)
