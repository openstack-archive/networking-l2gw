# Copyright 2017
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

import os

import networking_l2gw
from tempest.test_discover import plugins

from networking_l2gw.tests.tempest import config as l2gw_config


class NeutronL2gwTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(networking_l2gw.__file__)))[0]
        test_dir = "networking_l2gw/tests/api"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        conf.register_group(l2gw_config.l2gw_group)
        conf.register_opts(l2gw_config.L2GW_OPTS,
                           group=l2gw_config.l2gw_group)

    def get_opt_lists(self):
        return [
            (l2gw_config.l2gw_group.name, l2gw_config.L2GW_OPTS),
        ]
