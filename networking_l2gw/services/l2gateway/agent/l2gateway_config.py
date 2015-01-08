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
from networking_l2gw.services.l2gateway.common import constants as n_const

OVSDB_IP = 'ovsdb_ip'
OVSDB_PORT = 'ovsdb_port'
PRIVATE_KEY = 'private_key'
USE_SSL = 'use_ssl'
CERTIFICATE = 'certificate'
CA_CERT = 'ca_cert'


class L2GatewayConfig(object):
    def __init__(self, ovsdb_config):
        self.use_ssl = False
        if ovsdb_config.get(USE_SSL, None):
            self.use_ssl = ovsdb_config[USE_SSL]
            self.private_key = ovsdb_config[PRIVATE_KEY]
            self.certificate = ovsdb_config[CERTIFICATE]
            self.ca_cert = ovsdb_config[CA_CERT]

        self.ovsdb_identifier = ovsdb_config[n_const.OVSDB_IDENTIFIER]
        self.ovsdb_ip = ovsdb_config[OVSDB_IP]
        self.ovsdb_port = ovsdb_config[OVSDB_PORT]
        self.ovsdb_fd = None
