# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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
#    under the License.from oslo.config import cfg
from neutron.common import rpc as n_rpc
from neutron import context as ctx
from neutron.db import agents_db
from neutron.openstack.common import log as logging

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.services.l2gateway import agent_scheduler
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import topics

from oslo.config import cfg
from oslo import messaging

LOG = logging.getLogger(__name__)


class L2GatewayCallbacks(object):
    """RPC call back functions for L2gateway."""

    def __init__(self, plugin):
        super(L2GatewayCallbacks, self).__init__()
        self.plugin = plugin


class L2gatewayAgentApi(object):
    """L2gateway plugin to agent RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, context, host):
        """Initialize L2gateway plugin."""
        self.context = context
        target = messaging.Target(topic=topic, version=self.API_VERSION)
        self.client = n_rpc.get_client(target)

    def set_monitor_agent(self, hostname):
        """RPC to select Monitor/Transact agent."""
        cctxt = self.client.prepare(fanout=True)
        return cctxt.cast(self.context,
                          'set_monitor_agent',
                          hostname=hostname)


class L2GatewayPlugin(l2gateway_db.L2GatewayMixin):

    """Implementation of the Neutron l2 gateway Service Plugin.

    This class manages the workflow of L2 gateway request/response.
    """

    supported_extension_aliases = ["l2-gateway",
                                   "l2-gateway-connection"]

    def __init__(self):
        """Do the initialization for the l2 gateway service plugin here."""
        self.endpoints = [L2GatewayCallbacks(self),
                          agents_db.AgentExtRpcCallback()]
        self.conn = n_rpc.create_connection(new=True)
        self.conn.create_consumer(topics.L2GATEWAY_PLUGIN,
                                  self.endpoints,
                                  fanout=False)
        self.conn.consume_in_threads()
        context = ctx.get_admin_context()
        self.agent_rpc = L2gatewayAgentApi(topics.L2GATEWAY_AGENT,
                                           context,
                                           cfg.CONF.host)
        super(L2GatewayPlugin, self).__init__()
        LOG.debug("starting l2gateway agent scheduler")
        self.start_l2gateway_agent_scheduler()

    def start_l2gateway_agent_scheduler(self):
        """Start l2gateway agent scheduler thread."""
        self.agentscheduler = agent_scheduler.L2GatewayAgentScheduler()
        self.agentscheduler.initialize_thread()

    def get_plugin_type(self):
        """Get type of the plugin."""
        return constants.L2GW

    def get_plugin_description(self):
        """Get description of the plugin."""
        return "Neutron L2 gateway Service Plugin"
