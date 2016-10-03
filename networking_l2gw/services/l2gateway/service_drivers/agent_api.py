# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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

from neutron.common import rpc as n_rpc

from networking_l2gw._i18n import _
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc

import oslo_messaging as messaging


class L2gatewayAgentApi(object):
    """L2gateway plugin to agent RPC API."""

    API_VERSION = '1.0'

    def __init__(self, topic, host):
        """Initialize L2gateway plugin."""
        self.host = host
        target = messaging.Target(topic=topic, version=self.API_VERSION)
        self.client = n_rpc.get_client(target)

    def set_monitor_agent(self, context, hostname):
        """RPC to select Monitor/Transact agent."""
        cctxt = self.client.prepare(fanout=True)
        return cctxt.cast(context,
                          'set_monitor_agent',
                          hostname=hostname)

    def add_vif_to_gateway(self, context, ovsdb_identifier, logical_switch,
                           physical_locator, mac_remote):
        """RPC to enter the VM MAC details to gateway."""
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'add_vif_to_gateway',
                          ovsdb_identifier=ovsdb_identifier,
                          logical_switch_dict=logical_switch,
                          locator_dict=physical_locator,
                          mac_dict=mac_remote)

    def update_vif_to_gateway(self, context, ovsdb_identifier,
                              physical_locator, mac_remote):
        """RPC to update the VM MAC details to gateway."""
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'update_vif_to_gateway',
                          ovsdb_identifier=ovsdb_identifier,
                          locator_dict=physical_locator,
                          mac_dict=mac_remote)

    def delete_vif_from_gateway(self, context, ovsdb_identifier,
                                logical_switch_uuid, macs):
        """RPC to delete the VM MAC details from gateway."""
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'delete_vif_from_gateway',
                          ovsdb_identifier=ovsdb_identifier,
                          logical_switch_uuid=logical_switch_uuid,
                          mac=macs)

    def delete_network(self, context, ovsdb_identifier, logical_switch_uuid):
        """RPC to delete the Network from gateway."""
        cctxt = self.client.prepare()
        return cctxt.cast(context,
                          'delete_network',
                          ovsdb_identifier=ovsdb_identifier,
                          logical_switch_uuid=logical_switch_uuid)

    def _validate_request_op_method(self, context, op_method):
        """validate the method in the request."""
        method_list = [n_const.CREATE, n_const.DELETE]
        if op_method not in method_list:
            raise l2gw_exc.InvalidMethod(op_method=op_method)

    def update_connection_to_gateway(self, context, ovsdb_identifier,
                                     ls_dict, locator_list, mac_dict,
                                     port_dict, op_method):
        """RPC to update the connection to gateway."""
        self._validate_request_op_method(context, op_method)
        cctxt = self.client.prepare()
        try:
            return cctxt.call(context,
                              'update_connection_to_gateway',
                              ovsdb_identifier=ovsdb_identifier,
                              logical_switch_dict=ls_dict,
                              locator_dicts=locator_list,
                              mac_dicts=mac_dict,
                              port_dicts=port_dict,
                              op_method=op_method)
        except messaging.MessagingTimeout:
            message = _("Communication error with the L2 gateway agent")
            raise l2gw_exc.OVSDBError(message=message)
        except Exception as ex:
            message = str(ex)
            msg_splits = message.split('\n')
            raise l2gw_exc.OVSDBError(message="Error on the OVSDB "
                                      "server: " + msg_splits[0])
