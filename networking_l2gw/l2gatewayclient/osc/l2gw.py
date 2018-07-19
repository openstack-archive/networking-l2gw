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

from osc_lib.cli import format_columns
from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient._i18n import _
from neutronclient.common import utils
from neutronclient.osc import utils as nc_osc_utils

LOG = logging.getLogger(__name__)

INTERFACE_DELIMITER = ";"
SEGMENTATION_ID_DELIMITER = "#"
INTERFACE_SEG_ID_DELIMITER = "|"

L2_GATEWAY = 'l2_gateway'
L2_GATEWAYS = '%ss' % L2_GATEWAY

path = 'l2-gateways'
object_path = '/%s' % path
resource_path = '/%s/%%s' % path

_attr_map = (
    ('id', 'ID', column_util.LIST_BOTH),
    ('tenant_id', 'Tenant', column_util.LIST_LONG_ONLY),
    ('name', 'Name', column_util.LIST_BOTH),
    ('devices', 'Devices', column_util.LIST_BOTH),
)
_formatters = {
    'devices': format_columns.ListDictColumn,
}


def _get_common_parser(parser):
    """Adds to parser arguments common to create and update commands.

    :params ArgumentParser parser: argparse object contains all command's
                                   arguments
    """
    parser.add_argument(
        '--device',
        metavar='name=name,interface_names=INTERFACE-DETAILS',
        action='append', dest='devices', type=utils.str2dict,
        help=_('Device name and Interface-names of l2gateway. '
               'INTERFACE-DETAILS is of form '
               '\"<interface_name1>;[<interface_name2>]'
               '[|<seg_id1>[#<seg_id2>]]\" '
               '(--device option can be repeated)'))


def get_interface(interfaces):
    interface_dict = []
    for interface in interfaces:
        if INTERFACE_SEG_ID_DELIMITER in interface:
            int_name = interface.split(INTERFACE_SEG_ID_DELIMITER)[0]
            segid = interface.split(INTERFACE_SEG_ID_DELIMITER)[1]
            if SEGMENTATION_ID_DELIMITER in segid:
                segid = segid.split(SEGMENTATION_ID_DELIMITER)
            else:
                segid = [segid]
            interface_detail = {'name': int_name, 'segmentation_id': segid}
        else:
            interface_detail = {'name': interface}
        interface_dict.append(interface_detail)
    return interface_dict


def _args2body(parsed_args, update=False):
        if parsed_args.devices:
            devices = parsed_args.devices
            interfaces = []
        else:
            devices = []
        device_dict = []
        for device in devices:
            if 'interface_names' in device.keys():
                interface = device['interface_names']
                if INTERFACE_DELIMITER in interface:
                    interface_dict = interface.split(INTERFACE_DELIMITER)
                    interfaces = get_interface(interface_dict)
                else:
                    interfaces = get_interface([interface])
            if 'name' in device.keys():
                device = {'device_name': device['name'],
                          'interfaces': interfaces}
            else:
                device = {'interfaces': interfaces}
            device_dict.append(device)
        if parsed_args.name:
            l2gw_name = parsed_args.name
            body = {L2_GATEWAY: {'name': l2gw_name,
                                 'devices': device_dict}, }
        else:
            body = {L2_GATEWAY: {'devices': device_dict}, }
        return body


class CreateL2gw(command.ShowOne):
    _description = _("Create l2gateway resource")

    def get_parser(self, prog_name):
        parser = super(CreateL2gw, self).get_parser(prog_name)
        nc_osc_utils.add_project_owner_option_to_parser(parser)
        parser.add_argument(
            'name', metavar='<GATEWAY-NAME>',
            help=_('Descriptive name for logical gateway.'))
        _get_common_parser(parser)
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        attrs = {}
        if parsed_args.name is not None:
            attrs['name'] = str(parsed_args.name)
        if parsed_args.devices is not None:
            attrs['devices'] = str(parsed_args.devices)
        if 'project' in parsed_args and parsed_args.project is not None:
            project_id = nc_osc_utils.find_project(
                self.app.client_manager.identity,
                parsed_args.project,
                parsed_args.project_domain,
            ).id
            attrs['tenant_id'] = project_id
        body = _args2body(parsed_args)
        obj = client.post(object_path, body)[L2_GATEWAY]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns,
                                             formatters=_formatters)
        return display_columns, data


class ListL2gw(command.Lister):
    _description = _("List l2gateway that belongs to a given tenant")

    def get_parser(self, prog_name):
        parser = super(ListL2gw, self).get_parser(prog_name)
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
        objs = client.list(L2_GATEWAYS, object_path,
                           retrieve_all=True, params=params)[L2_GATEWAYS]
        headers, columns = column_util.get_column_definitions(
            _attr_map, long_listing=True)
        return (headers, (osc_utils.get_dict_properties(
            s, columns, formatters=_formatters) for s in objs))


class ShowL2gw(command.ShowOne):
    _description = _("Show information of a given l2gateway")

    def get_parser(self, prog_name):
        parser = super(ShowL2gw, self).get_parser(prog_name)
        parser.add_argument(
            L2_GATEWAY,
            metavar="<L2_GATEWAY>",
            help=_("ID or name of l2_gateway to look up."),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        id = client.find_resource(L2_GATEWAY, parsed_args.l2_gateway)['id']
        obj = client.get(resource_path % id)[L2_GATEWAY]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns,
                                             formatters=_formatters)
        return display_columns, data


class DeleteL2gw(command.Command):
    _description = _("Delete a given l2gateway")

    def get_parser(self, prog_name):
        parser = super(DeleteL2gw, self).get_parser(prog_name)
        parser.add_argument(
            L2_GATEWAYS,
            metavar="<L2_GATEWAY>",
            nargs="+",
            help=_("ID(s) or name(s) of l2_gateway to delete."),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        fails = 0
        for id_or_name in parsed_args.l2_gateways:
            try:
                id = client.find_resource(L2_GATEWAY, id_or_name)['id']
                client.delete(resource_path % id)
                LOG.warning("L2 Gateaway %(id)s deleted", {'id': id})
            except Exception as e:
                fails += 1
                LOG.error("Failed to delete L2 Gateway with name or ID "
                          "'%(id_or_name)s': %(e)s",
                          {'id_or_name': id_or_name, 'e': e})
        if fails > 0:
            msg = (_("Failed to delete %(fails)s of %(total)s L2 Gateway.") %
                   {'fails': fails, 'total': len(parsed_args.l2_gateways)})
            raise exceptions.CommandError(msg)


class UpdateL2gw(command.ShowOne):
    _description = _("Update a given l2gateway")

    def get_parser(self, prog_name):
        parser = super(UpdateL2gw, self).get_parser(prog_name)
        parser.add_argument(
            L2_GATEWAY,
            metavar="<L2_GATEWAY>",
            help=_("ID or name of l2_gateway to update."),
        )
        parser.add_argument('--name', metavar='name',
                            help=_('Descriptive name for logical gateway.'))
        _get_common_parser(parser)
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        id = client.find_resource(L2_GATEWAY, parsed_args.l2_gateway)['id']
        if parsed_args.devices:
            body = _args2body(parsed_args)
        else:
            body = {L2_GATEWAY: {'name': parsed_args.name}}
        obj = client.put(resource_path % id, body)[L2_GATEWAY]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns,
                                             formatters=_formatters)
        return display_columns, data
