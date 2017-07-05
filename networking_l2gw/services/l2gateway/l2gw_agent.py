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

import sys

from neutron.common import config as common_config
from neutron.common import rpc as n_rpc
from neutron.conf.agent import common as agent_config
from oslo_config import cfg
from oslo_service import service

from networking_l2gw.services.l2gateway.agent.ovsdb import manager
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.common import topics


class L2gatewayAgentService(n_rpc.Service):
    def start(self):
        super(L2gatewayAgentService, self).start()


def main():
    config.register_ovsdb_opts_helper(cfg.CONF)
    agent_config.register_agent_state_opts_helper(cfg.CONF)
    common_config.init(sys.argv[1:])
    config.setup_logging()

    mgr = manager.OVSDBManager(cfg.CONF)
    svc = L2gatewayAgentService(
        host=cfg.CONF.host,
        topic=topics.L2GATEWAY_AGENT,
        manager=mgr
    )
    service.launch(cfg.CONF, svc).wait()
