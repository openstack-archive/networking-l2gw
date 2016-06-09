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

from neutron.common import rpc as n_rpc

import oslo_messaging as messaging


class L2GatewayAgentApi(object):
    """Agent side of the Agent to Plugin RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, host):
        self.host = host
        target = messaging.Target(topic=topic, version=self.API_VERSION)
        self.client = n_rpc.get_client(target)

    def update_ovsdb_changes(self, context, activity, ovsdb_data):
        cctxt = self.client.prepare()
        return cctxt.cast(context,
                          'update_ovsdb_changes',
                          activity=activity,
                          ovsdb_data=ovsdb_data)

    def notify_ovsdb_states(self, context, ovsdb_states):
        cctxt = self.client.prepare()
        return cctxt.cast(context,
                          'notify_ovsdb_states',
                          ovsdb_states=ovsdb_states)
