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

from networking_l2gw.services.l2gateway import exceptions as l2gw_exc

from oslo_log import log as logging
import oslo_messaging as messaging

LOG = logging.getLogger(__name__)


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

    def update_connection_to_gateway(self, context, ovsdb_identifier,
                                     ls_dict, locator_list, mac_dict,
                                     port_dict):
        """RPC to update the connection to gateway."""
        cctxt = self.client.prepare()
        try:
            return cctxt.call(context,
                              'update_connection_to_gateway',
                              ovsdb_identifier=ovsdb_identifier,
                              logical_switch_dict=ls_dict,
                              locator_dicts=locator_list,
                              mac_dicts=mac_dict,
                              port_dicts=port_dict)
        except messaging.MessagingTimeout:
            message = _("Communication error with the L2 gateway agent")
            raise l2gw_exc.OVSDBError(message=message)
        except Exception as ex:
            message = str(ex)
            msg_splits = message.split('\n')
            raise l2gw_exc.OVSDBError(message="Error on the OVSDB "
                                      "server: " + msg_splits[0])

    def create_remote_unknown(self, context, ovsdb_identifier,
                              remote_gw_connection):
        LOG.debug("Sending create unknown to agent for ipaddr: '%s', "
                  "seg_id: '%s'", remote_gw_connection['ipaddr'],
                  remote_gw_connection['seg_id'])
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'create_remote_unknown',
                          ovsdb_identifier=ovsdb_identifier,
                          network_id=remote_gw_connection['network'],
                          ipaddr=remote_gw_connection['ipaddr'],
                          seg_id=remote_gw_connection['seg_id']
                          )

    def delete_l2_remote_gateway_connection(self, context,
                                            ovsdb_identifier,
                                            network_id,
                                            ipaddr,
                                            tunnel_key):
        LOG.debug("Sending delete remote connection to agent for "
                  "network: '%s' ipaddr: '%s', tunnel_key: '%s'",
                  network_id, ipaddr, tunnel_key)
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'del_remote_connection',
                          ovsdb_identifier=ovsdb_identifier,
                          network_id=network_id,
                          ipaddr=ipaddr,
                          tunnel_key=tunnel_key)

    def add_ucast_mac_remote(self, context, ovsdb_identifier,
                             logical_sw_uuid, locator, mac, ipaddr):
        LOG.debug("Adding UCAST MAC '%s' to locator '%s'", mac, locator)
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'add_ucast_mac_remote',
                          ovsdb_identifier=ovsdb_identifier,
                          logical_sw_uuid=logical_sw_uuid,
                          locator=locator,
                          mac=mac,
                          ipaddr=ipaddr)

    def del_ucast_mac_remote(self, context, ovsdb_identifier, mac_uuid):
        LOG.debug("Sending deleting UCAST MAC '%s' from OVSDB '%s' to agent",
                  mac_uuid, ovsdb_identifier)
        cctxt = self.client.prepare()
        return cctxt.call(context,
                          'del_ucast_mac_remote',
                          ovsdb_identifier=ovsdb_identifier,
                          mac_uuid=mac_uuid)
