# Copyright 2015 OpenStack Foundation.
# All Rights Reserved
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

"""
Command-line interface to the L2gateway APIs
"""
from __future__ import print_function

import sys

from cliff import commandmanager
from neutronclient.common import clientmanager
from neutronclient.common import exceptions as exc
from neutronclient import shell as neutronshell
from oslo.utils import encodeutils

from networking_l2gw.l2gatewayclient.l2gateway.v2_0 import l2gateway
from networking_l2gw.l2gatewayclient.l2gateway.v2_0 import l2gateway_connection

VERSION = '2.0'
NEUTRON_API_VERSION = '2.0'
clientmanager.neutron_client.API_VERSIONS = {
    '2.0': 'networking_l2gw.l2gatewayclient.v2_0.client.Client',
}

COMMAND_V2 = {
    'l2-gateway-create': l2gateway.Createl2gateway,
    'l2-gateway-list': l2gateway.Listl2gateway,
    'l2-gateway-show': l2gateway.Showl2gateway,
    'l2-gateway-delete': l2gateway.Deletel2gateway,
    'l2-gateway-update': l2gateway.Updatel2gateway,
    'l2-gateway-connection-create': (l2gateway_connection.
                                     Createl2gatewayConnection),
    'l2-gateway-connection-list': (l2gateway_connection.
                                   Listl2gatewayConnection),
    'l2-gateway-connection-show': (l2gateway_connection.
                                   Showl2gatewayConnection),
    'l2-gateway-connection-delete': (l2gateway_connection.
                                     Deletel2gatewayConnection),
}

COMMANDS = {'2.0': COMMAND_V2}


class L2gatewayShell(neutronshell.NeutronShell):

    def __init__(self, apiversion):
        super(neutronshell.NeutronShell, self).__init__(
            description=__doc__.strip(),
            version=VERSION,
            command_manager=commandmanager.CommandManager('l2gateway.cli'), )
        self.commands = COMMANDS
        for k, v in self.commands[apiversion].items():
            self.command_manager.add_command(k, v)

        # This is instantiated in initialize_app() only when using
        # password flow auth
        self.auth_client = None
        self.api_version = apiversion


def main(argv=sys.argv[1:]):
    try:
        return L2gatewayShell(NEUTRON_API_VERSION).run(list(map(
            encodeutils.safe_decode, argv)))
    except exc.NeutronClientException:
        return 1
    except Exception as e:
        print(unicode(e))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
