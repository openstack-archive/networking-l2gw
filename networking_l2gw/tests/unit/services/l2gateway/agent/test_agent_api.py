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
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.agent_rpc = agent_api.L2GatewayAgentApi(
            self.topic, self.host)
        super(L2GatewayAgentApiTestCase, self).setUp()

    def test_update_ovsdb_changes(self):
        cctxt = mock.Mock()
        context = mock.Mock()
        fake_activity = 1
        self.agent_rpc.client.prepare.return_value = cctxt
        self.agent_rpc.update_ovsdb_changes(context, fake_activity, mock.ANY)
        cctxt.cast.assert_called_with(
            context, 'update_ovsdb_changes',
            activity=fake_activity, ovsdb_data=mock.ANY)

    def test_notify_ovsdb_states(self):
        cctxt = mock.Mock()
        context = mock.Mock()
        self.agent_rpc.client.prepare.return_value = cctxt
        self.agent_rpc.notify_ovsdb_states(context, mock.ANY)
        cctxt.cast.assert_called_with(
            context, 'notify_ovsdb_states', ovsdb_states=mock.ANY)
