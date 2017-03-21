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

from networking_l2gw.db.l2gateway import l2gateway_db
from networking_l2gw.db.l2gateway.ovsdb import lib as db
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway.common import topics
from networking_l2gw.services.l2gateway.common import tunnel_calls
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc
from networking_l2gw.services.l2gateway.service_drivers import agent_api

from neutron_lib.api.definitions import portbindings
from neutron_lib import constants
from neutron_lib.plugins import directory
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

LOG = logging.getLogger(__name__)


class L2GatewayOVSDBCallbacks(object):
    """Implement the rpc call back functions from OVSDB."""

    target = messaging.Target(version='1.0')

    def __init__(self, plugin):
        super(L2GatewayOVSDBCallbacks, self).__init__()
        self.plugin = plugin
        self.ovsdb = None

    def update_ovsdb_changes(self, context, activity, ovsdb_data):
        """RPC to update the changes from OVSDB in the database."""
        self.ovsdb = self.get_ovsdbdata_object(
            ovsdb_data.get(n_const.OVSDB_IDENTIFIER))
        self.ovsdb.update_ovsdb_changes(context, activity, ovsdb_data)

    def notify_ovsdb_states(self, context, ovsdb_states):
        """RPC to notify the OVSDB servers connection state."""
        if ovsdb_states:
            self.ovsdb = self.get_ovsdbdata_object(
                list(ovsdb_states.keys())[0])
        if self.ovsdb:
            LOG.debug("ovsdb_states = %s", ovsdb_states)
            self.ovsdb.notify_ovsdb_states(context, ovsdb_states)

    def get_ovsdbdata_object(self, ovsdb_identifier):
        return OVSDBData(ovsdb_identifier)


class OVSDBData(object):
    """Process the data coming from OVSDB."""

    def __init__(self, ovsdb_identifier=None):
        self.ovsdb_identifier = ovsdb_identifier
        self._setup_entry_table()
        self.agent_rpc = agent_api.L2gatewayAgentApi(
            topics.L2GATEWAY_AGENT, cfg.CONF.host)
        self.l2gw_mixin = l2gateway_db.L2GatewayMixin()
        self.core_plugin = directory.get_plugin()
        self.tunnel_call = tunnel_calls.Tunnel_Calls()

    def _cleanup_all_ovsdb_tables(self, context, ovsdb_identifier):
        db.delete_all_physical_locators_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_physical_switches_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_physical_ports_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_logical_switches_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_ucast_macs_locals_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_ucast_macs_remotes_by_ovsdb_identifier(
            context, ovsdb_identifier)
        db.delete_all_vlan_bindings_by_ovsdb_identifier(
            context, ovsdb_identifier)

    def update_ovsdb_changes(self, context, activity, ovsdb_data):
        """RPC to update the changes from OVSDB in the database."""
        ovsdb_identifier = ovsdb_data.get('ovsdb_identifier')
        if not activity:
            self._cleanup_all_ovsdb_tables(context, ovsdb_identifier)
        for item, value in ovsdb_data.items():
            lookup = self.entry_table.get(item, None)
            if lookup:
                lookup(context, value)
        if ovsdb_data.get('new_remote_macs'):
            self._handle_l2pop(context, ovsdb_data.get('new_remote_macs'))

    def notify_ovsdb_states(self, context, ovsdb_states):
        """RPC to notify the OVSDB servers connection state."""
        for ovsdb_identifier, state in ovsdb_states.items():
            if state == 'connected':
                pending_recs = db.get_all_pending_remote_macs_in_asc_order(
                    context, ovsdb_identifier)
                if pending_recs:
                    for pending_mac in pending_recs:
                        logical_switch_uuid = pending_mac['logical_switch_uuid'
                                                          ]
                        mac = pending_mac['mac']
                        operation = pending_mac['operation']
                        try:
                            if operation == 'insert' or operation == 'update':
                                l_switch = ovsdb_schema.LogicalSwitch(
                                    logical_switch_uuid, None, None, None)
                                locator_uuid = pending_mac.get(
                                    'locator_uuid', None)
                                dst_ip = pending_mac.get(
                                    'dst_ip', None)
                                locator = ovsdb_schema.PhysicalLocator(
                                    locator_uuid, dst_ip)
                                mac_remote = ovsdb_schema.UcastMacsRemote(
                                    pending_mac.get('uuid', None),
                                    mac,
                                    logical_switch_uuid,
                                    locator_uuid,
                                    pending_mac['vm_ip'])
                                if operation == 'insert':
                                    self.agent_rpc.add_vif_to_gateway(
                                        context,
                                        ovsdb_identifier,
                                        l_switch.__dict__,
                                        locator.__dict__,
                                        mac_remote.__dict__)
                                else:
                                    # update operation
                                    self.agent_rpc.update_vif_to_gateway(
                                        context,
                                        ovsdb_identifier,
                                        locator.__dict__,
                                        mac_remote.__dict__)
                            else:
                                self.agent_rpc.delete_vif_from_gateway(
                                    context, ovsdb_identifier,
                                    logical_switch_uuid, [mac])

                            # As the pending operation is over, delete the
                            # record from the pending_ucast_mac_remote table
                            db.delete_pending_ucast_mac_remote(
                                context,
                                operation,
                                ovsdb_identifier,
                                logical_switch_uuid,
                                mac)
                        except Exception as ex:
                            LOG.exception("Exception occurred = %s",
                                          str(ex))

    def _setup_entry_table(self):
        self.entry_table = {'new_logical_switches':
                            self._process_new_logical_switches,
                            'new_physical_ports':
                            self._process_new_physical_ports,
                            'new_physical_switches':
                            self._process_new_physical_switches,
                            'new_physical_locators':
                            self._process_new_physical_locators,
                            'new_local_macs':
                            self._process_new_local_macs,
                            'new_remote_macs':
                            self._process_new_remote_macs,
                            'modified_remote_macs':
                            self._process_modified_remote_macs,
                            'modified_physical_ports':
                            self._process_modified_physical_ports,
                            'deleted_logical_switches':
                            self._process_deleted_logical_switches,
                            'deleted_physical_ports':
                            self._process_deleted_physical_ports,
                            'deleted_physical_switches':
                            self._process_deleted_physical_switches,
                            'deleted_physical_locators':
                            self._process_deleted_physical_locators,
                            'deleted_local_macs':
                            self._process_deleted_local_macs,
                            'deleted_remote_macs':
                            self._process_deleted_remote_macs,
                            'modified_physical_switches':
                            self._process_modified_physical_switches,
                            }

        return

    def _process_new_logical_switches(self,
                                      context,
                                      new_logical_switches):
        for logical_switch in new_logical_switches:
            ls_dict = logical_switch
            ls_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            l_switch = db.get_logical_switch(context, ls_dict)
            if not l_switch:
                db.add_logical_switch(context, ls_dict)

    def _process_new_physical_switches(self,
                                       context,
                                       new_physical_switches):
        for physical_switch in new_physical_switches:
            ps_dict = physical_switch
            ps_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            if (ps_dict.get('tunnel_ip'))[0] == 'set':
                ps_dict['tunnel_ip'] = None
            p_switch = db.get_physical_switch(context, ps_dict)
            if not p_switch:
                db.add_physical_switch(context, ps_dict)

    def _process_new_physical_ports(self,
                                    context,
                                    new_physical_ports):
        for physical_port in new_physical_ports:
            pp_dict = physical_port
            pp_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            p_port = db.get_physical_port(context, pp_dict)
            if not p_port:
                db.add_physical_port(context, pp_dict)
            if pp_dict.get('vlan_bindings'):
                for vlan_binding in pp_dict.get('vlan_bindings'):
                    vlan_binding[
                        n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
                    vlan_binding['port_uuid'] = pp_dict.get('uuid')
                    v_binding = db.get_vlan_binding(context, vlan_binding)
                    if not v_binding:
                        db.add_vlan_binding(context, vlan_binding)

    def _process_new_physical_locators(self,
                                       context,
                                       new_physical_locators):
        for physical_locator in new_physical_locators:
            pl_dict = physical_locator
            pl_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            p_locator = db.get_physical_locator(context, pl_dict)
            if not p_locator:
                db.add_physical_locator(context, pl_dict)

    def _process_new_local_macs(self,
                                context,
                                new_local_macs):
        for local_mac in new_local_macs:
            lm_dict = local_mac
            lm_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            lm_dict['logical_switch_uuid'] = local_mac.get('logical_switch_id')
            l_mac = db.get_ucast_mac_local(context, lm_dict)
            if not l_mac:
                db.add_ucast_mac_local(context, lm_dict)

    def _process_new_remote_macs(self,
                                 context,
                                 new_remote_macs):
        for remote_mac in new_remote_macs:
            rm_dict = remote_mac
            rm_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            r_mac = db.get_ucast_mac_remote(context, rm_dict)
            if not r_mac:
                db.add_ucast_mac_remote(context, rm_dict)

    def _process_modified_remote_macs(self,
                                      context,
                                      modified_remote_macs):
        for remote_mac in modified_remote_macs:
            remote_mac[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            db.update_ucast_mac_remote(context, remote_mac)

    def _get_physical_switch_ips(self, context, mac):
        physical_switch_ips = set()
        record_dict = {n_const.OVSDB_IDENTIFIER: self.ovsdb_identifier}
        vlan_bindings = db.get_all_vlan_bindings_by_logical_switch(
            context, mac)
        for vlan_binding in vlan_bindings:
            record_dict['uuid'] = vlan_binding.get('port_uuid')
            physical_port = db.get_physical_port(context, record_dict)
            record_dict['uuid'] = physical_port.get('physical_switch_id')
            physical_switch = db.get_physical_switch(context, record_dict)
            physical_switch_ips.add(physical_switch.get('tunnel_ip'))
        return list(physical_switch_ips)

    def _get_agent_by_mac(self, context, mac):
        host = None
        mac_addr = mac.get('mac')
        port = self._get_port_by_mac(context, mac_addr)
        for port_dict in port:
            host = port_dict[portbindings.HOST_ID]
        agent_l2_pop_enabled = self._get_agent_details_by_host(context, host)
        return agent_l2_pop_enabled

    def _get_port_by_mac(self, context, mac_addr):
        port = self.core_plugin.get_ports(
            context, filters={'mac_address': [mac_addr]})
        return port

    def _get_agent_details_by_host(self, context, host):
        l2_agent = None
        agent_l2_pop_enabled = None
        agents = self.core_plugin.get_agents(
            context, filters={'host': [host]})
        for agent in agents:
            agent_tunnel_type = agent['configurations'].get('tunnel_types', [])
            agent_l2_pop_enabled = agent['configurations'].get('l2_population',
                                                               None)
            if n_const.VXLAN in agent_tunnel_type:
                l2_agent = agent
                break
        if not l2_agent:
            raise l2gw_exc.L2AgentNotFoundByHost(
                host=host)
        return agent_l2_pop_enabled

    def _handle_l2pop(self, context, new_remote_macs):
        """handle vxlan tunnel creation based on whether l2pop is enabled or not.

        if l2pop is enabled in L2 agent on a host to which port belongs, then
        call add_fdb_entries. otherwise, call tunnel_sync.
        """
        for mac in new_remote_macs:
            try:
                agent_l2_pop_enabled = self._get_agent_by_mac(context, mac)
            except l2gw_exc.L2AgentNotFoundByHost as e:
                LOG.debug(e.message)
                continue
            physical_switches = self._get_physical_switch_ips(context, mac)
            for physical_switch in physical_switches:
                other_fdb_entries = self._get_fdb_entries(
                    context, physical_switch, mac.get('logical_switch_id'))
                if agent_l2_pop_enabled:
                    self.tunnel_call.trigger_l2pop_sync(context,
                                                        other_fdb_entries)
                else:
                    self.tunnel_call.trigger_tunnel_sync(context,
                                                         physical_switch)

    def _process_modified_physical_ports(self,
                                         context,
                                         modified_physical_ports):
        for physical_port in modified_physical_ports:
            pp_dict = physical_port
            pp_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            modified_port = db.get_physical_port(context, pp_dict)
            if modified_port:
                db.update_physical_ports_status(context, pp_dict)
                port_vlan_bindings = physical_port.get('vlan_bindings')
                vlan_bindings = db.get_all_vlan_bindings_by_physical_port(
                    context, pp_dict)
                for vlan_binding in vlan_bindings:
                    db.delete_vlan_binding(context, vlan_binding)
                for port_vlan_binding in port_vlan_bindings:
                    port_vlan_binding['port_uuid'] = pp_dict['uuid']
                    port_vlan_binding[
                        n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
                    db.add_vlan_binding(context, port_vlan_binding)
            else:
                db.add_physical_port(context, pp_dict)

    def _process_modified_physical_switches(self, context,
                                            modified_physical_switches):
        for physical_switch in modified_physical_switches:
            db.update_physical_switch_status(context, physical_switch)

    def _process_deleted_logical_switches(self,
                                          context,
                                          deleted_logical_switches):
        for logical_switch in deleted_logical_switches:
            ls_dict = logical_switch
            ls_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            db.delete_logical_switch(context, ls_dict)

    def _process_deleted_physical_switches(self,
                                           context,
                                           deleted_physical_switches):
        for physical_switch in deleted_physical_switches:
            ps_dict = physical_switch
            ps_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            db.delete_physical_switch(context, ps_dict)
        physical_switches = db.get_all_physical_switches_by_ovsdb_id(
            context, self.ovsdb_identifier)
        if not physical_switches:
            logical_switches = db.get_all_logical_switches_by_ovsdb_id(
                context, self.ovsdb_identifier)
            if logical_switches:
                for logical_switch in logical_switches:
                    self.agent_rpc.delete_network(
                        context, self.ovsdb_identifier,
                        logical_switch.get('uuid'))

    def _process_deleted_physical_ports(self,
                                        context,
                                        deleted_physical_ports):
        for physical_port in deleted_physical_ports:
            pp_dict = physical_port
            pp_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            port_name = pp_dict['name']
            p_port = db.get_physical_port(context, pp_dict)
            if not p_port:
                raise l2gw_exc.L2GatewayInterfaceNotFound(
                    interface_id=port_name)
            p_switch_id = p_port.get('physical_switch_id')
            switch_dict = {}
            switch_dict['uuid'] = p_switch_id
            switch_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            switch_db = db.get_physical_switch(context, switch_dict)
            if not switch_db:
                raise l2gw_exc.L2GatewayDeviceNotFound(
                    device_id=p_switch_id)
            switch_name = switch_db.get('name')
            l2gw_id_list = self.l2gw_mixin._get_l2gw_ids_by_interface_switch(
                context, port_name, switch_name)
            if l2gw_id_list:
                for l2gw_id in l2gw_id_list:
                    self.l2gw_mixin._delete_connection_by_l2gw_id(context,
                                                                  l2gw_id)
            vlan_bindings = db.get_all_vlan_bindings_by_physical_port(
                context, pp_dict)
            ls_set = set()
            for vlan_binding in vlan_bindings:
                vlan_binding['logical_switch_id'] = vlan_binding.get(
                    'logical_switch_uuid')
                if vlan_binding.get('logical_switch_uuid') in ls_set:
                    db.delete_vlan_binding(context, vlan_binding)
                    continue
                bindings = db.get_all_vlan_bindings_by_logical_switch(
                    context, vlan_binding)
                if bindings and len(bindings) == 1:
                    self._delete_macs_from_ovsdb(
                        context,
                        vlan_binding.get('logical_switch_uuid'),
                        self.ovsdb_identifier)
                elif bindings and len(bindings) > 1:
                    flag = True
                    for binding in bindings:
                        if binding[
                           'ovsdb_identifier'] == self.ovsdb_identifier:
                            flag = False
                            break
                    if flag:
                        self._delete_macs_from_ovsdb(
                            context,
                            vlan_binding.get('logical_switch_uuid'),
                            self.ovsdb_identifier)
                ls_set.add(vlan_binding.get('logical_switch_uuid'))
                db.delete_vlan_binding(context, vlan_binding)
            db.delete_physical_port(context, pp_dict)

    def _delete_macs_from_ovsdb(self, context, logical_switch_id,
                                ovsdb_identifier):
        mac_list = []
        ls_dict = {'logical_switch_id': logical_switch_id,
                   'ovsdb_identifier': ovsdb_identifier}
        macs = db.get_all_ucast_mac_remote_by_ls(context, ls_dict)
        for mac in macs:
            mac_list.append(mac.get('mac'))
        self.agent_rpc.delete_vif_from_gateway(
            context, ovsdb_identifier,
            logical_switch_id, mac_list)

    def _process_deleted_physical_locators(self,
                                           context,
                                           deleted_physical_locators):
        physical_switch_ips = []
        logical_switch_ids = self._get_logical_switch_ids(context)
        physical_switches = db.get_all_physical_switches_by_ovsdb_id(
            context, self.ovsdb_identifier)
        for physical_switch in physical_switches:
            physical_switch_ips.append(
                physical_switch.get('tunnel_ip'))
        tunneling_ip_dict = self._get_agent_ips(context)
        for physical_locator in deleted_physical_locators:
            pl_dict = physical_locator
            pl_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            agent_ip = physical_locator.get('dst_ip')
            if agent_ip in tunneling_ip_dict.keys():
                for logical_switch_id in logical_switch_ids:
                    for physical_switch_ip in physical_switch_ips:
                        other_fdb_entries = self._get_fdb_entries(
                            context, physical_switch_ip, logical_switch_id)
                        agent_host = tunneling_ip_dict.get(agent_ip)
                        self.tunnel_call.trigger_l2pop_delete(
                            context, other_fdb_entries, agent_host)
            else:
                for logical_switch_id in logical_switch_ids:
                    other_fdb_entries = self._get_fdb_entries(
                        context, agent_ip, logical_switch_id)
                    self.tunnel_call.trigger_l2pop_delete(
                        context, other_fdb_entries)
            db.delete_physical_locator(context, pl_dict)

    def _process_deleted_local_macs(self,
                                    context,
                                    deleted_local_macs):
        for local_mac in deleted_local_macs:
            lm_dict = local_mac
            lm_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            db.delete_ucast_mac_local(context, lm_dict)

    def _process_deleted_remote_macs(self,
                                     context,
                                     deleted_remote_macs):
        for remote_mac in deleted_remote_macs:
            rm_dict = remote_mac
            rm_dict[n_const.OVSDB_IDENTIFIER] = self.ovsdb_identifier
            db.delete_ucast_mac_remote(context, rm_dict)

    def _get_logical_switch_ids(self, context):
        logical_switch_ids = set()
        logical_switches = db.get_all_logical_switches_by_ovsdb_id(
            context, self.ovsdb_identifier)
        for logical_switch in logical_switches:
                logical_switch_ids.add(logical_switch.get('uuid'))
        return list(logical_switch_ids)

    def _get_agent_ips(self, context):
        agent_ip_dict = {}
        agents = self.core_plugin.get_agents(
            context)
        for agent in agents:
            conf_dict_tunnel_type = agent['configurations'].get(
                "tunnel_types", [])
            if n_const.VXLAN in conf_dict_tunnel_type:
                tunnel_ip = agent['configurations'].get('tunneling_ip')
                agent_ip_dict[tunnel_ip] = agent.get('host')
        return agent_ip_dict

    def _get_fdb_entries(self, context, agent_ip, logical_switch_uuid):
        ls_dict = {'uuid': logical_switch_uuid,
                   n_const.OVSDB_IDENTIFIER: self.ovsdb_identifier}
        logical_switch = db.get_logical_switch(context, ls_dict)
        network_id = logical_switch.get('name')
        segment_id = logical_switch.get('key')
        port_fdb_entries = constants.FLOODING_ENTRY
        other_fdb_entries = {network_id: {'segment_id': segment_id,
                                          'network_type': 'vxlan',
                                          'ports': {agent_ip:
                                                    [port_fdb_entries]
                                                    }}}
        return other_fdb_entries
