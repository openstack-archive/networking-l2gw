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

from neutron.common import config as common_config
from neutron.tests import base

from oslo_config import cfg

from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway import l2gw_agent as agent


class TestL2gwAgent(base.BaseTestCase):
    def setUp(self):
        super(TestL2gwAgent, self).setUp()
        config.register_ovsdb_opts_helper(cfg.CONF)

    def test_start(self):
        with mock.patch.object(
            agent.n_rpc.Service, 'start'
        ) as mock_start:
            mgr = mock.Mock()
            cfg.CONF.periodic_interval = mock.Mock(return_value=10)
            agent_service = agent.L2gatewayAgentService('host',
                                                        'topic', mgr)
            agent_service.start()
            self.assertTrue(mock_start.called)

    def test_main_l2gw_agent(self):
        logging_str = 'neutron.conf.agent.common.setup_logging'
        common_config_str = mock.patch.object(common_config, 'init').start()
        with mock.patch.object(common_config_str, 'init'), \
                mock.patch(logging_str), \
                mock.patch.object(agent.service, 'launch') as mock_launch, \
                mock.patch('sys.argv'), \
                mock.patch.object(agent.manager, 'OVSDBManager'), \
                mock.patch.object(cfg.CONF, 'register_opts'):
            agent.main()
            mock_launch.assert_called_once_with(cfg.CONF, mock.ANY)
