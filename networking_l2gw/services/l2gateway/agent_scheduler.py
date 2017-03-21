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
#    under the License.

import random

from neutron_lib.plugins import directory
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall

from neutron.db import agents_db
from neutron_lib import context as neutron_context

from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import constants as srv_const

LOG = logging.getLogger(__name__)


class L2GatewayAgentScheduler(agents_db.AgentDbMixin):
    """L2gateway agent scheduler class.

    This maintains active and inactive agents and
    select monitor and transact agents.
    """
    _plugin = None
    _l2gwplugin = None

    def __init__(self, agent_rpc, notifier=None):
        super(L2GatewayAgentScheduler, self).__init__()
        self.notifier = notifier
        config.register_l2gw_opts_helper()
        self.monitor_interval = cfg.CONF.periodic_monitoring_interval
        self.agent_rpc = agent_rpc

    @property
    def l2gwplugin(self):
        if self._l2gwplugin is None:
            self._l2gwplugin = directory.get_plugin(srv_const.L2GW)
        return self._l2gwplugin

    @property
    def plugin(self):
        if self._plugin is None:
            self._plugin = directory.get_plugin()
        return self._plugin

    def initialize_thread(self):
        """Initialization of L2gateway agent scheduler thread."""
        try:
            monitor_thread = loopingcall.FixedIntervalLoopingCall(
                self.monitor_agent_state)
            monitor_thread.start(
                interval=self.monitor_interval,
                initial_delay=random.randint(self.monitor_interval,
                                             self.monitor_interval * 2))
            LOG.debug("Successfully initialized L2gateway agent scheduler"
                      " thread with loop interval %s", self.monitor_interval)
        except Exception:
            LOG.error("Cannot initialize agent scheduler thread")

    def _select_agent_type(self, context, agents_to_process):
        """Select the Monitor agent."""
        # Various cases to be handled:
        # 1. Check if there is a single active L2 gateway agent.
        #    If only one agent is active, then make it the Monitor agent.
        # 2. Else, in the list of the active agents, if there does not
        #    exist Monitor agent, then make the agent that
        #    started first as the Monitor agent.
        # 3. If multiple Monitor agents exist (case where the Monitor agent
        #    gets disconnected from the Neutron server and another agent
        #    becomes the Monitor agent and then the original Monitor agent
        #    connects back within the agent downtime value), then we need to
        #    send the fanout message so that only one becomes the Monitor
        #    agent.

        # Check if there already exists Monitor agent and it's the only one.
        monitor_agents = [x for x in agents_to_process
                          if x['configurations'].get(srv_const.L2GW_AGENT_TYPE)
                          == srv_const.MONITOR]
        if len(monitor_agents) == 1:
            return

        # We either have more than one Monitor agent,
        # or there does not exist Monitor agent.
        # We will decide which agent should be the Monitor agent.
        chosen_agent = None
        if len(agents_to_process) == 1:
            # Only one agent is configured.
            # Make it the Monitor agent
            chosen_agent = agents_to_process[0]
        else:
            # Select the agent with the oldest started_at
            # timestamp as the Monitor agent.
            sorted_active_agents = sorted(agents_to_process,
                                          key=lambda k: k['started_at'])
            chosen_agent = sorted_active_agents[0]
        self.agent_rpc.set_monitor_agent(context, chosen_agent['host'])

    def monitor_agent_state(self):
        """Represents L2gateway agent scheduler thread.

        Maintains list of active and inactive agents based on
        the heartbeat recorded.
        """
        context = neutron_context.get_admin_context()
        try:
            all_agents = self.plugin.get_agents(
                context,
                filters={'agent_type': [srv_const.AGENT_TYPE_L2GATEWAY]})
        except Exception:
            LOG.exception("Unable to get the agent list. Continuing...")
            return

        # Reset the agents that will be processed for selecting the
        # Monitor agent
        agents_to_process = []
        for agent in all_agents:
            if not self.is_agent_down(agent['heartbeat_timestamp']):
                agents_to_process.append(agent)
        if agents_to_process:
            self._select_agent_type(context, agents_to_process)
        return
