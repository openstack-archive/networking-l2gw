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

from neutron.common import topics as neutron_topics
from neutron.plugins.ml2.drivers.l2pop import rpc as l2pop_rpc
from neutron.plugins.ml2 import managers
from neutron.plugins.ml2 import rpc as rpc


class Tunnel_Calls(object):
    """Common tunnel calls for L2 agent."""
    def __init__(self):
        self._construct_rpc_stuff()

    def _construct_rpc_stuff(self):
        self.notifier = rpc.AgentNotifierApi(neutron_topics.AGENT)
        self.type_manager = managers.TypeManager()
        self.tunnel_rpc_obj = rpc.RpcCallbacks(self.notifier,
                                               self.type_manager)

    def trigger_tunnel_sync(self, context, tunnel_ip):
        """Sends tunnel sync RPC message to the neutron

        L2 agent.
        """
        tunnel_dict = {'tunnel_ip': tunnel_ip,
                       'tunnel_type': 'vxlan'}
        self.tunnel_rpc_obj.tunnel_sync(context,
                                        **tunnel_dict)

    def trigger_l2pop_sync(self, context, other_fdb_entries):
        """Sends L2pop ADD RPC message to the neutron L2 agent."""
        l2pop_rpc.L2populationAgentNotifyAPI(
            ).add_fdb_entries(context, other_fdb_entries)

    def trigger_l2pop_delete(self, context, other_fdb_entries, host=None):
        """Sends L2pop DELETE RPC message to the neutron L2 agent."""
        l2pop_rpc.L2populationAgentNotifyAPI(
            ).remove_fdb_entries(context, other_fdb_entries, host)
