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
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import topics

from oslo.config import cfg
from oslo import messaging
from oslo_utils import importutils

LOG = logging.getLogger(__name__)


class L2gatewayAgentApi(object):
    """L2gateway plugin to agent RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, context, host):
        """Initialize L2gateway plugin."""
        self.context = context
        self.host = host
        target = messaging.Target(topic=topic, version=self.API_VERSION)
        self.client = n_rpc.get_client(target)

    def set_monitor_agent(self, hostname):
        """RPC to select Monitor/Transact agent."""
        cctxt = self.client.prepare(fanout=True)
        return cctxt.cast(self.context,
                          'set_monitor_agent',
                          hostname=hostname)

    def add_vif_to_gateway(self, context, record_dict):
        """RPC to enter the VM MAC details to gateway."""
        cctxt = self.client.prepare()
        return cctxt.cast(self.context,
                          'add_vif_to_gateway',
                          record_dict=record_dict)

    def delete_vif_from_gateway(self, context, record_dict):
        """RPC to delete the VM MAC details from gateway."""
        cctxt = self.client.prepare()
        return cctxt.cast(self.context,
                          'delete_vif_from_gateway',
                          record_dict=record_dict)

    def delete_network(self, context, record_dict):
        """RPC to delete the Network from gateway."""
        cctxt = self.client.prepare()
        return cctxt.cast(self.context,
                          'delete_network',
                          record_dict=record_dict)

    def update_connection_to_gateway(self, context, record_dict):
        """RPC to update the connection to gateway."""
        cctxt = self.client.prepare()
        return cctxt.cast(self.context,
                          'update_connection_to_gateway',
                          record_dict=record_dict)


class L2GatewayPlugin(l2gateway_db.L2GatewayMixin):

    """Implementation of the Neutron l2 gateway Service Plugin.

    This class manages the workflow of L2 gateway request/response.
    """

    supported_extension_aliases = ["l2-gateway",
                                   "l2-gateway-connection"]

    def __init__(self):
        """Do the initialization for the l2 gateway service plugin here."""
        config.register_l2gw_opts_helper()
        l2gatewaycallback = cfg.CONF.l2gw_callback_class
        self.endpoints = [importutils.import_object(l2gatewaycallback, self),
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
        l2gateway_db.subscribe()
        self.start_l2gateway_agent_scheduler()

    def start_l2gateway_agent_scheduler(self):
        """Start l2gateway agent scheduler thread."""
        self.agentscheduler = agent_scheduler.L2GatewayAgentScheduler()
        self.agentscheduler.initialize_thread()

    def add_vif_to_gateway(self, context, port_dict):
        pass

    def delete_vif_from_gateway(self, context, port_dict):
        pass

    def create_l2_gateway_connection(self, context, l2_gateway_connection):
        pass

    def delete_l2_gateway_connection(self, context, l2_gateway_connection):
        pass

    def get_plugin_type(self):
        """Get type of the plugin."""
        return constants.L2GW

    def get_plugin_description(self):
        """Get description of the plugin."""
        return "Neutron L2 gateway Service Plugin"
