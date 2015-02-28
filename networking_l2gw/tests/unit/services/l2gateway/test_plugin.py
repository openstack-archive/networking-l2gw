# Copyright (c) 2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mock

import contextlib
from neutron.common import rpc as n_rpc
from neutron import context as ctx
from neutron.db import agents_db
from neutron.tests import base

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway import plugin as l2gw_plugin

from oslo_utils import importutils


class TestL2GatewayAgentApi(base.BaseTestCase):

    def setUp(self):
        self.client_mock_p = mock.patch.object(n_rpc, 'get_client')
        self.client_mock = self.client_mock_p.start()
        self.context = mock.ANY
        self.topic = 'foo_topic'
        self.host = 'foo_host'

        self.plugin_rpc = l2gw_plugin.L2gatewayAgentApi(
            self.topic, self.context, self.host)
        super(TestL2GatewayAgentApi, self).setUp()

    def test_add_vif_to_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.add_vif_to_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'add_vif_to_gateway', record_dict=mock.ANY)

    def test_delete_vif_from_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_vif_from_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_vif_from_gateway', record_dict=mock.ANY)

    def test_delete_network(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.delete_network(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'delete_network', record_dict=mock.ANY)

    def test_update_connection_to_gateway(self):
        cctxt = mock.Mock()
        self.plugin_rpc.client.prepare.return_value = cctxt
        self.plugin_rpc.update_connection_to_gateway(self.context, mock.ANY)
        cctxt.cast.assert_called_with(
            self.context, 'update_connection_to_gateway',
            record_dict=mock.ANY)

    def test_l2gatewayplugin_init(self):
        with contextlib.nested(
            mock.patch.object(config,
                              'register_l2gw_opts_helper'),
            mock.patch.object(importutils,
                              'import_object'),
            mock.patch.object(agents_db,
                              'AgentExtRpcCallback'),
            mock.patch.object(n_rpc,
                              'create_connection'),
            mock.patch.object(n_rpc.Connection,
                              'create_consumer'),
            mock.patch.object(n_rpc.Connection,
                              'consume_in_threads'),
            mock.patch.object(ctx,
                              'get_admin_context'),
            mock.patch.object(l2gw_plugin,
                              'L2gatewayAgentApi'),
            mock.patch.object(l2gw_plugin.LOG,
                              'debug'),
            mock.patch.object(l2gw_plugin.L2GatewayPlugin,
                              'start_l2gateway_agent_scheduler'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '__init__'),
            mock.patch.object(l2gateway_db,
                              'subscribe')
        ) as (reg_l2gw_opts,
              import_obj,
              agent_calback,
              create_conn,
              create_consum,
              consume_in_thread,
              get_admin_ctx,
              l2gw_api,
              debug,
              scheduler,
              super_init,
              subscribe):
            l2gw_plugin.L2GatewayPlugin()
            reg_l2gw_opts.assert_called()
            import_obj.assert_called()
            agent_calback.assert_called()
            create_conn.assert_called()
            create_consum.assert_called()
            consume_in_thread.assert_called()
            get_admin_ctx.assert_called()
            l2gw_api.assert_called()
            debug.assert_called()
            scheduler.assert_called()
            super_init.assert_called()
            subscribe.assert_called()
