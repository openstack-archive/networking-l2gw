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

from neutron.agent.common import config as agent_config
from neutron.agent import rpc as agent_rpc
from neutron.openstack.common import loopingcall
from neutron.tests import base

from oslo.config import cfg

from networking_l2gw.services.l2gateway.agent import (base_agent_manager
                                                      as l2gw_manager)
from networking_l2gw.services.l2gateway.agent import agent_api
from networking_l2gw.services.l2gateway.common import constants as n_const


class TestBaseAgentManager(base.BaseTestCase):

    def setUp(self):
        super(TestBaseAgentManager, self).setUp()
        self.conf = cfg.CONF
        agent_config.register_agent_state_opts_helper(self.conf)
        cfg.CONF.set_override('report_interval', 1, 'AGENT')
        self.context = mock.Mock
        mock_conf = mock.Mock()
        self.l2gw_agent_manager = l2gw_manager.BaseAgentManager(
            mock_conf)

    def test_init(self):
        with mock.patch.object(agent_api,
                               'L2GatewayAgentApi') as l2_gw_agent_api:
            with mock.patch.object(l2gw_manager.BaseAgentManager,
                                   '_setup_state_rpc') as setup_state_rpc:
                self.l2gw_agent_manager.__init__(mock.Mock())
                self.assertEqual(self.l2gw_agent_manager.l2gw_agent_type,
                                 n_const.TRANSACT)
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

    def test_report_state(self):
        with mock.patch('neutron.agent.rpc.PluginReportStateAPI') as state_api:
            l2_gw = l2gw_manager.BaseAgentManager(mock.Mock())
            self.assertTrue(l2_gw.agent_state['start_flag'])
            original_state = l2_gw.agent_state
            original_use_call = l2_gw.use_call
            self.assertTrue(l2_gw.use_call)
            l2_gw._report_state()
            self.assertFalse(l2_gw.agent_state['start_flag'])
            self.assertFalse(l2_gw.use_call)
            state_api_inst = state_api.return_value
            state_api_inst.report_state.assert_called_once_with(
                l2_gw.context, original_state, original_use_call)

    def test_report_state_Exception(self):
        with mock.patch('neutron.agent.rpc.PluginReportStateAPI') as state_api:
            with mock.patch.object(l2gw_manager.LOG, 'exception') as exc:
                state_api_inst = state_api.return_value
                self.l2gw_agent_manager._report_state()
                state_api_inst.report_state.side_effect = Exception
                exc.assertCalled()

    def test_agent_updated(self):
        fake_payload = {'fake_key': 'fake_value'}
        with mock.patch.object(l2gw_manager.LOG, 'info') as logger_call:
            self.l2gw_agent_manager.agent_updated(mock.Mock(), fake_payload)
            self.assertEqual(1, logger_call.call_count)

    def test_set_l2gateway_agent_type_monitor(self):
        l2_gw_agent_type = n_const.MONITOR
        self.l2gw_agent_manager.set_l2gateway_agent_type(
            self.context, l2_gw_agent_type)
        self.assertEqual(self.l2gw_agent_manager.l2gw_agent_type,
                         l2_gw_agent_type)
        self.assertEqual(
            self.l2gw_agent_manager.agent_state.get(
                'configurations')[n_const.L2GW_AGENT_TYPE], l2_gw_agent_type)

    def test_set_l2gateway_agent_type_transact(self):
        l2_gw_agent_type = n_const.TRANSACT
        self.l2gw_agent_manager.set_l2gateway_agent_type(
            self.context, l2_gw_agent_type)
        self.assertEqual(self.l2gw_agent_manager.l2gw_agent_type,
                         l2_gw_agent_type)
        self.assertEqual(
            self.l2gw_agent_manager.agent_state.get(
                'configurations')[n_const.L2GW_AGENT_TYPE], l2_gw_agent_type)

    def test_set_l2gateway_agent_type_transactmonitor(self):
        l2_gw_agent_type = '+'.join([n_const.MONITOR, n_const.TRANSACT])
        self.l2gw_agent_manager.set_l2gateway_agent_type(
            self.context, l2_gw_agent_type)
        self.assertEqual(self.l2gw_agent_manager.l2gw_agent_type,
                         l2_gw_agent_type)
        self.assertEqual(
            self.l2gw_agent_manager.agent_state.get(
                'configurations')[n_const.L2GW_AGENT_TYPE], l2_gw_agent_type)

    def test_set_l2gateway_agent_type_invalid(self):
        l2_gw_agent_type = 'fake_type'
        result = self.l2gw_agent_manager.set_l2gateway_agent_type(
            self.context, l2_gw_agent_type)
        self.assertTrue(result, n_const.L2GW_INVALID_RPC_MSG_FORMAT)
