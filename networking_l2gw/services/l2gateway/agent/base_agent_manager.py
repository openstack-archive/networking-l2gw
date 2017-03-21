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

from neutron.agent import rpc as agent_rpc
from neutron_lib import context

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_service import periodic_task

from networking_l2gw.services.l2gateway.agent import agent_api
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import topics

LOG = logging.getLogger(__name__)


class BaseAgentManager(periodic_task.PeriodicTasks):
    """Basic agent manager that handles basic RPCs and report states."""

    def __init__(self, conf=None):
        conf = getattr(self, "conf", cfg.CONF)
        super(BaseAgentManager, self).__init__(conf)
        self.l2gw_agent_type = ''
        self.gateways = {}
        self.plugin_rpc = agent_api.L2GatewayAgentApi(
            topics.L2GATEWAY_PLUGIN,
            self.conf.host
        )
        self._get_agent_state()
        self.admin_state_up = True
        self._setup_state_rpc()

    def _get_agent_state(self):
        self.agent_state = {
            'binary': 'neutron-l2gateway-agent',
            'host': self.conf.host,
            'topic': topics.L2GATEWAY_AGENT,
            'configurations': {
                'report_interval': self.conf.AGENT.report_interval,
                n_const.L2GW_AGENT_TYPE: self.l2gw_agent_type,
            },
            'start_flag': True,
            'agent_type': n_const.AGENT_TYPE_L2GATEWAY}

    def _setup_state_rpc(self):
        self.state_rpc = agent_rpc.PluginReportStateAPI(
            topics.L2GATEWAY_PLUGIN)
        report_interval = self.conf.AGENT.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)

    def _report_state(self):
        try:
            ctx = context.get_admin_context_without_session()
            self.state_rpc.report_state(ctx, self.agent_state,
                                        True)
            self.agent_state['start_flag'] = False
        except Exception:
            LOG.exception("Failed reporting state!")
            self.handle_report_state_failure()

    def handle_report_state_failure(self):
        pass

    def agent_updated(self, context, payload):
        LOG.info("agent_updated by server side %s!", payload)

    def set_monitor_agent(self, context, hostname):
        """Handle RPC call from plugin to update agent type.

        RPC call from the plugin to accept that I am a monitoring
        or a transact agent. This is a fanout cast message
        """
        if hostname == self.conf.host:
            self.l2gw_agent_type = n_const.MONITOR
        else:
            self.l2gw_agent_type = ''

        self.agent_state.get('configurations')[n_const.L2GW_AGENT_TYPE
                                               ] = self.l2gw_agent_type
