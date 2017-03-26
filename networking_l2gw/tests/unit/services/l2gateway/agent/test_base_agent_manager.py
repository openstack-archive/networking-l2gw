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

from neutron.agent import rpc as agent_rpc
from neutron.conf.agent import common as agent_config
from neutron.tests import base

from oslo_config import cfg
from oslo_service import loopingcall

from networking_l2gw.services.l2gateway.agent import (base_agent_manager
                                                      as l2gw_manager)
from networking_l2gw.services.l2gateway.agent import agent_api
from networking_l2gw.services.l2gateway.common import constants as n_const


class TestBaseAgentManager(base.BaseTestCase):

    def setUp(self):
        super(TestBaseAgentManager, self).setUp()
        agent_config.register_agent_state_opts_helper(cfg.CONF)
        cfg.CONF.set_override('report_interval', 1, 'AGENT')
        self.context = mock.Mock
        mock.patch('neutron.agent.rpc.PluginReportStateAPI').start()
        self.l2gw_agent_manager = l2gw_manager.BaseAgentManager(
            cfg.CONF)

    def test_init(self):
        with mock.patch.object(agent_api,
                               'L2GatewayAgentApi') as l2_gw_agent_api:
            with mock.patch.object(l2gw_manager.BaseAgentManager,
                                   '_setup_state_rpc') as setup_state_rpc:
                self.l2gw_agent_manager.__init__(mock.Mock())
                self.assertEqual('',
                                 self.l2gw_agent_manager.l2gw_agent_type)
                self.assertTrue(self.l2gw_agent_manager.admin_state_up)
                self.assertTrue(setup_state_rpc.called)
                self.assertTrue(l2_gw_agent_api.called)

    def test_setup_state_rpc(self):
        cfg.CONF.set_override('report_interval', 1, 'AGENT')
        with mock.patch.object(agent_rpc,
                               'PluginReportStateAPI'
                               ) as agent_report_state_rpc:
            with mock.patch.object(loopingcall,
                                   'FixedIntervalLoopingCall'
                                   ) as looping_call:
                self.l2gw_agent_manager._setup_state_rpc()
                self.assertTrue(agent_report_state_rpc.called)
                self.assertTrue(looping_call.called)
                looping_call.return_value.start.assert_called_with(
                    interval=mock.ANY)

    def test_report_state(self):
        with mock.patch.object(self.l2gw_agent_manager,
                               'state_rpc') as state_api:
            self.assertTrue(self.l2gw_agent_manager.agent_state['start_flag'])
            self.l2gw_agent_manager._report_state()
            self.assertFalse(self.l2gw_agent_manager.agent_state['start_flag'])
            self.assertTrue(state_api.report_state.called)

    def test_report_state_exception(self):
        cfg.CONF.set_override('report_interval', 1, 'AGENT')
        with mock.patch.object(self.l2gw_agent_manager,
                               'state_rpc') as state_rpc:
            with mock.patch.object(l2gw_manager.LOG, 'exception') as exc:
                with mock.patch.object(self.l2gw_agent_manager,
                                       'handle_report_state_failure'
                                       ) as mock_handle_report_state_failure:
                    state_rpc.report_state.side_effect = Exception()
                    self.l2gw_agent_manager._report_state()
                    self.assertTrue(exc.called)
                    self.assertTrue(mock_handle_report_state_failure.called)

    def test_agent_updated(self):
        fake_payload = {'fake_key': 'fake_value'}
        with mock.patch.object(l2gw_manager.LOG, 'info') as logger_call:
            self.l2gw_agent_manager.agent_updated(mock.Mock(), fake_payload)
            self.assertEqual(1, logger_call.call_count)

    def test_set_monitor_agent_type_monitor(self):
        self.l2gw_agent_manager.l2gw_agent_type = ''
        self.l2gw_agent_manager.conf.host = 'fake_host'
        self.l2gw_agent_manager.set_monitor_agent(self.context, 'fake_host')
        self.assertEqual(n_const.MONITOR,
                         self.l2gw_agent_manager.agent_state.
                         get('configurations')[n_const.L2GW_AGENT_TYPE])
        self.assertEqual(n_const.MONITOR,
                         self.l2gw_agent_manager.l2gw_agent_type)

    def test_set_monitor_agent_type_transact(self):
        self.l2gw_agent_manager.l2gw_agent_type = ''
        cfg.CONF.host = 'fake_host'
        self.l2gw_agent_manager.set_monitor_agent(
            self.context, 'fake_host1')
        self.assertNotEqual(n_const.MONITOR,
                            self.l2gw_agent_manager.agent_state.
                            get('configurations')[n_const.L2GW_AGENT_TYPE])
        self.assertEqual('',
                         self.l2gw_agent_manager.agent_state.
                         get('configurations')[n_const.L2GW_AGENT_TYPE])
        self.assertEqual('',
                         self.l2gw_agent_manager.l2gw_agent_type)
