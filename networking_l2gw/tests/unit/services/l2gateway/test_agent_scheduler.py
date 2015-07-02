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
#

import contextlib
import copy
import datetime

import mock
from oslo_config import cfg
from oslo_service import loopingcall
from oslo_utils import timeutils

from neutron.common import topics
from neutron import context as neutron_context
from neutron.db import agents_db
from neutron import manager
from neutron.plugins.ml2 import rpc
from neutron.tests import base

from networking_l2gw.services.l2gateway import agent_scheduler
from networking_l2gw.services.l2gateway.common import constants as srv_const


def make_active_agent(fake_id, fake_agent_type, config=None):
    agent_dict = dict(id=fake_id,
                      agent_type=fake_agent_type,
                      host='localhost_' + str(fake_id),
                      heartbeat_timestamp=timeutils.utcnow(),
                      started_at=timeutils.utcnow(),
                      configurations=config)
    return agent_dict


def make_inactive_agent(fake_id, fake_agent_type, delta, config=None):
    agent_dict = dict(id=fake_id,
                      agent_type=fake_agent_type,
                      host='remotehost_' + str(fake_id),
                      heartbeat_timestamp=(timeutils.utcnow() - datetime.
                                           timedelta(delta)),
                      configurations=config)
    return agent_dict


class FakePlugin(agents_db.AgentDbMixin):

    def __init__(self):
        self.notifier = rpc.AgentNotifierApi(topics.AGENT)


class TestAgentScheduler(base.BaseTestCase):

    fake_a_agent_list = []
    fake_i_agent_list = []

    def setUp(self):
        super(TestAgentScheduler, self).setUp()
        cfg.CONF.set_override('core_plugin',
                              "neutron.plugins.ml2.plugin.Ml2Plugin")
        self.plugin = FakePlugin()
        self.context = neutron_context.get_admin_context()
        cfg.CONF.set_override('agent_down_time', 10)
        cfg.CONF.set_override('periodic_monitoring_interval', 5)
        self.agentsch = agent_scheduler.L2GatewayAgentScheduler(cfg.CONF)
        self.agentsch._plugin = self.plugin
        self.agentsch.context = self.context
        self.agentsch.agent_ext_support = True
        self.LOG = agent_scheduler.LOG

    def populate_agent_lists(self, config=None):
        self.fake_a_agent_list = []
        self.fake_a_agent_list.append(make_active_agent(
            '1000', srv_const.AGENT_TYPE_L2GATEWAY, config))

        self.fake_i_agent_list = []
        self.fake_i_agent_list.append(make_inactive_agent(
            '2000', srv_const.AGENT_TYPE_L2GATEWAY, 52, config))

    def test_initialize_thread(self):
        with contextlib.nested(
            mock.patch.object(loopingcall, 'FixedIntervalLoopingCall'),
            mock.patch.object(self.LOG, 'debug'),
            mock.patch.object(self.LOG, 'error')
        ) as (loop_call, debug, err):
            self.agentsch.initialize_thread()
            self.assertTrue(loop_call.called)
            self.assertTrue(debug.called)
            self.assertFalse(err.called)

    def test_initialize_thread_loop_call_exception(self):
        with contextlib.nested(
            mock.patch.object(loopingcall, 'FixedIntervalLoopingCall',
                              side_effect=RuntimeError),
            mock.patch.object(self.LOG, 'error')
        ) as (loop_call, log_err):
            self.agentsch.initialize_thread()
            self.assertTrue(loop_call.called)
            self.assertTrue(log_err.called)

    def test_select_agent_type_one_active(self):
        config = {srv_const.L2GW_AGENT_TYPE: ''}
        self.populate_agent_lists(config)

        with contextlib.nested(
            mock.patch('__builtin__.sorted'),
            mock.patch.object(manager, 'NeutronManager'),
            mock.patch.object(self.LOG, 'exception')
        ) as (mock_sorted, mgr, logger_call):
            self.agentsch._l2gwplugin = mock.Mock()
            self.agentsch._select_agent_type(self.context,
                                             self.fake_a_agent_list)
            self.agentsch.l2gwplugin.agent_rpc.set_monitor_agent_called_with(
                self.context, self.fake_a_agent_list[0]['host'])

    def test_select_agent_type_multiple_active(self):
        config = {srv_const.L2GW_AGENT_TYPE: ''}
        self.populate_agent_lists(config)
        self.fake_a_agent_list.append(make_active_agent(
            '1001', srv_const.AGENT_TYPE_L2GATEWAY, config))
        self.agentsch._l2gwplugin = mock.Mock()

        with contextlib.nested(
            mock.patch.object(manager, 'NeutronManager'),
            mock.patch.object(self.LOG, 'exception')
        ) as (mgr, logger_call):
            self.agentsch._select_agent_type(self.context,
                                             self.fake_a_agent_list)
            self.agentsch.l2gwplugin.agent_rpc.set_monitor_agent_called_with(
                self.context, self.fake_a_agent_list[0]['host'])

    def test_monitor_agent_state(self):
        config = {srv_const.L2GW_AGENT_TYPE: ''}
        self.populate_agent_lists(config)
        fake_all_agent_list = copy.deepcopy(self.fake_i_agent_list)
        fake_all_agent_list.extend(self.fake_a_agent_list)
        self.fake_a_agent_list.append(make_active_agent(
            '1001', srv_const.AGENT_TYPE_L2GATEWAY, config))

        with contextlib.nested(
            mock.patch.object(self.agentsch, '_select_agent_type'),
            mock.patch.object(self.plugin, 'get_agents',
                              return_value=fake_all_agent_list),
            mock.patch.object(self.agentsch, 'is_agent_down',
                              return_value=False)
        ) as (select_agent, get_agent_list, is_agt):
            self.agentsch.monitor_agent_state()
            self.assertTrue(get_agent_list.called)
            self.assertTrue(select_agent.called)
            self.assertTrue(is_agt.called)

    def test_monitor_agent_state_exception_get_agents(self):
        with contextlib.nested(
            mock.patch.object(self.plugin, 'get_agents',
                              side_effect=Exception),
            mock.patch.object(self.LOG, 'exception')
        ) as (get_agent_list, exception_log):
            self.agentsch.monitor_agent_state()
            self.assertTrue(get_agent_list.called)
            self.assertTrue(exception_log.called)
