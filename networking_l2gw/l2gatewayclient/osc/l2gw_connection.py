# All Rights Reserved 2018
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

import logging

from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient._i18n import _
from neutronclient.neutron import v2_0 as n_v20
from neutronclient.osc import utils as nc_osc_utils

LOG = logging.getLogger(__name__)

L2_GATEWAY_CONNECTION = 'l2_gateway_connection'
L2_GATEWAY_CONNECTIONS = '%ss' % L2_GATEWAY_CONNECTION

path = 'l2-gateway-connections'
object_path = '/%s' % path
resource_path = '/%s/%%s' % path

_attr_map = (
    ('id', 'ID', column_util.LIST_BOTH),
    ('tenant_id', 'Tenant', column_util.LIST_LONG_ONLY),
    ('l2_gateway_id', 'L2 GateWay ID', column_util.LIST_BOTH),
    ('network_id', 'Network ID', column_util.LIST_BOTH),
    ('segmentation_id', 'Segmentation ID', column_util.LIST_BOTH),
)


class CreateL2gwConnection(command.ShowOne):
    _description = _("Create l2gateway-connection")

    def retrieve_ids(self, client, args):
        gateway_id = n_v20.find_resourceid_by_name_or_id(
            client, 'l2_gateway', args.gateway_name)
        network_id = n_v20.find_resourceid_by_name_or_id(
            client, 'network', args.network)
        return gateway_id, network_id

    def get_parser(self, prog_name):
        parser = super(CreateL2gwConnection, self).get_parser(prog_name)
        parser.add_argument('gateway_name', metavar='<GATEWAY-NAME/UUID>',
                            help=_('Descriptive name for logical gateway.'))
        parser.add_argument(
            'network', metavar='<NETWORK-NAME/UUID>',
            help=_('Network name or uuid.'))
        parser.add_argument(
            '--default-segmentation-id',
            dest='seg_id',
            help=_('default segmentation-id that will '
                   'be applied to the interfaces for which '
                   'segmentation id was not specified '
                   'in l2-gateway-create command.'))
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        (gateway_id, network_id) = self.retrieve_ids(client, parsed_args)
        body = {
            L2_GATEWAY_CONNECTION: {
                'l2_gateway_id': gateway_id, 'network_id': network_id
            }
        }
        if parsed_args.seg_id:
            body[L2_GATEWAY_CONNECTION]['segmentation_id'] = \
                parsed_args.seg_id
        obj = client.post(object_path, body)[L2_GATEWAY_CONNECTION]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns)
        return display_columns, data


class ListL2gwConnection(command.Lister):
    _description = _("List l2gateway-connections")

    def get_parser(self, prog_name):
        parser = super(ListL2gwConnection, self).get_parser(prog_name)
        nc_osc_utils.add_project_owner_option_to_parser(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        params = {}
        if parsed_args.project is not None:
            project_id = nc_osc_utils.find_project(
                self.app.client_manager.identity,
                parsed_args.project,
                parsed_args.project_domain,
            ).id
            params['tenant_id'] = project_id
        objs = client.list(
            L2_GATEWAY_CONNECTIONS, object_path,
            retrieve_all=True, params=params)[L2_GATEWAY_CONNECTIONS]
        headers, columns = column_util.get_column_definitions(
            _attr_map, long_listing=True)
        return (headers, (osc_utils.get_dict_properties(
            s, columns) for s in objs))


class ShowL2gwConnection(command.ShowOne):
    _description = _("Show information of a given l2gateway-connection")

    def get_parser(self, prog_name):
        parser = super(ShowL2gwConnection, self).get_parser(prog_name)
        parser.add_argument(
            L2_GATEWAY_CONNECTION,
            metavar="<L2_GATEWAY_CONNECTION>",
            help=_("ID of l2_gateway_connection to look up."),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        id = client.find_resource(L2_GATEWAY_CONNECTION,
                                  parsed_args.l2_gateway_connection)['id']
        obj = client.get(resource_path % id)[L2_GATEWAY_CONNECTION]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns)
        return display_columns, data


class DeleteL2gwConnection(command.Command):
    _description = _("Delete a given l2gateway-connection")

    def get_parser(self, prog_name):
        parser = super(DeleteL2gwConnection, self).get_parser(prog_name)
        parser.add_argument(
            L2_GATEWAY_CONNECTIONS,
            metavar="<L2_GATEWAY_CONNECTIONS>",
            nargs="+",
            help=_("ID(s) of l2_gateway_connections(s) to delete."),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        fails = 0
        for id_or_name in parsed_args.l2_gateway_connections:
            try:
                id = client.find_resource(
                    L2_GATEWAY_CONNECTION, id_or_name)['id']
                client.delete(resource_path % id)
                LOG.warning("L2 Gateaway Connection %(id)s deleted",
                            {'id': id})
            except Exception as e:
                fails += 1
                LOG.error("Failed to delete L2 Gateway Connection with name "
                          "or ID '%(id_or_name)s': %(e)s",
                          {'id_or_name': id_or_name, 'e': e})
        if fails > 0:
            msg = (_("Failed to delete %(fails)s of %(total)s L2 Gateway "
                     "Connection.") %
                   {'fails': fails, 'total': len(
                       parsed_args.l2_gateway_connections)})
            raise exceptions.CommandError(msg)
