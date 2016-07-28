# Copyright (c) 2016 OpenStack Foundation
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

from neutron.plugins.ml2.drivers.l2pop import rpc as l2pop_rpc
from neutron.plugins.ml2.drivers import type_tunnel
from neutron.plugins.ml2 import managers
from neutron.plugins.ml2 import rpc as rpc
from neutron.tests import base

from networking_l2gw.services.l2gateway.common import tunnel_calls


class TestTunnelCalls(base.BaseTestCase):

    def setUp(self):
        super(TestTunnelCalls, self).setUp()
        mock.patch.object(managers, 'TypeManager').start()
        self.tunnel_call = tunnel_calls.Tunnel_Calls()
        self.context = mock.MagicMock()

    def test_trigger_tunnel_sync(self):
        with mock.patch.object(rpc, 'RpcCallbacks'), \
                mock.patch.object(type_tunnel.TunnelRpcCallbackMixin,
                                  'tunnel_sync') as mock_tunnel_sync:
            self.tunnel_call.trigger_tunnel_sync(self.context, 'fake_ip')
            mock_tunnel_sync.assert_called_with(
                self.context, tunnel_ip='fake_ip', tunnel_type='vxlan')

    def test_trigger_l2pop_sync(self):
        fake_fdb_entry = "fake_fdb_entry"
        with mock.patch.object(l2pop_rpc.L2populationAgentNotifyAPI,
                               'add_fdb_entries') as (mock_add_fdb):
            self.tunnel_call.trigger_l2pop_sync(self.context,
                                                fake_fdb_entry)
            mock_add_fdb.assert_called_with(self.context,
                                            fake_fdb_entry)

    def test_trigger_l2pop_delete(self):
        fake_fdb_entry = "fake_fdb_entry"
        fake_host = 'fake_host'
        with mock.patch.object(l2pop_rpc.L2populationAgentNotifyAPI,
                               'remove_fdb_entries') as (mock_delete_fdb):
            self.tunnel_call.trigger_l2pop_delete(self.context,
                                                  fake_fdb_entry, fake_host)
            mock_delete_fdb.assert_called_with(self.context,
                                               fake_fdb_entry, fake_host)
