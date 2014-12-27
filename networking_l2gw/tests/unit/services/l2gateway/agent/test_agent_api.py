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

import mock

from neutron.tests import base

from networking_l2gw.services.l2gateway.agent import agent_api


class L2GatewayAgentApiTestCase(base.BaseTestCase):

    def setUp(self):
        self.client_mock_p = mock.patch.object(agent_api.n_rpc, 'get_client')
        self.client_mock = self.client_mock_p.start()
        self.ctxt = mock.ANY
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.agent_rpc = agent_api.L2GatewayAgentApi(
            self.topic, self.ctxt, self.host)
        super(L2GatewayAgentApiTestCase, self).setUp()

    def test_update_ovsdb_changes(self):
        cctxt = mock.Mock()
        self.agent_rpc.client.prepare.return_value = cctxt
        self.agent_rpc.update_ovsdb_changes(mock.ANY)
        cctxt.call.assert_called_with(
            self.ctxt, 'update_ovsdb_changes', ovsdb_data=mock.ANY)
