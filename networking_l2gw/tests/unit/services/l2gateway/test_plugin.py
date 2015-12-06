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
from neutron.tests import base

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.services.l2gateway.common import config
from networking_l2gw.services.l2gateway.ovsdb import data
from networking_l2gw.services.l2gateway import plugin as l2gw_plugin


class TestL2GatewayPlugin(base.BaseTestCase):

    def setUp(self):
        super(TestL2GatewayPlugin, self).setUp()
        load_driver = mock.MagicMock()
        self.plugin = mock.MagicMock()
        self.plugin._load_drivers.return_value = load_driver
        self.plugin._get_driver_for_provider.return_value = load_driver
        self.ovsdb_identifier = 'fake_ovsdb_id'
        self.ovsdb_data = data.OVSDBData(self.ovsdb_identifier)
        self.context = mock.ANY

    def test_l2gatewayplugin_init(self):
        with contextlib.nested(
            mock.patch.object(config,
                              'register_l2gw_opts_helper'),
            mock.patch.object(l2gw_plugin.L2GatewayPlugin,
                              '_load_drivers'),
            mock.patch.object(l2gateway_db.L2GatewayMixin,
                              '__init__'),
            mock.patch.object(l2gateway_db,
                              'subscribe')
        ) as (reg_l2gw_opts,
              load_drivers,
              super_init,
              subscribe):
            l2gw_plugin.L2GatewayPlugin()
            self.assertTrue(reg_l2gw_opts.called)
            self.assertTrue(load_drivers.called)
            self.assertTrue(super_init.called)
            self.assertTrue(subscribe.called)
