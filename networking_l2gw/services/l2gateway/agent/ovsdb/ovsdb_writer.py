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

import random
import socket

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils

from networking_l2gw.services.l2gateway.agent.ovsdb import base_connection
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions

LOG = logging.getLogger(__name__)


class OVSDBWriter(base_connection.BaseConnection):
    """Performs transactions to OVSDB server tables."""
    def __init__(self, conf, gw_config, mgr=None):
        super(OVSDBWriter, self).__init__(conf, gw_config, mgr=None)
        self.mgr = mgr

    def _process_response(self, op_id):
        result = self._response(op_id)
        error = result.get("error", None)
        if error:
            raise exceptions.OVSDBError(
                message="Error from the OVSDB server: %s" % error
                )
        # Check errors in responses of all the subqueries
        outcomes = result.get("result", None)
        if outcomes:
            for outcome in outcomes:
                error = outcome.get("error", None)
                if error:
                    raise exceptions.OVSDBError(
                        message="Error from the OVSDB server: %s" % error)
        return result

    def _get_reply(self, operation_id, ovsdb_identifier):
        count = 0
        while count <= n_const.MAX_RETRIES:
            response = self._recv_data(ovsdb_identifier)
            LOG.debug("Response from OVSDB server = %s", str(response))
            if response:
                try:
                    json_m = jsonutils.loads(response)
                    self.responses.append(json_m)
                    method_type = json_m.get('method', None)
                    if method_type == "echo" and self.enable_manager:
                        self.ovsdb_dicts.get(ovsdb_identifier).send(
                            jsonutils.dumps(
                                {"result": json_m.get("params", None),
                                 "error": None, "id": json_m['id']}))
                    else:
                        if self._process_response(operation_id):
                            return True
                except Exception as ex:
                    with excutils.save_and_reraise_exception():
                        LOG.exception("Exception while receiving the "
                                      "response for the write request:"
                                      " [%s]", ex)
            count += 1
        with excutils.save_and_reraise_exception():
            LOG.error("Could not obtain response from the OVSDB server "
                      "for the request")

    def _send_and_receive(self, query, operation_id, ovsdb_identifier,
                          rcv_required):
        if not self.send(query, addr=ovsdb_identifier):
            return
        if rcv_required:
            self._get_reply(operation_id, ovsdb_identifier)

    def delete_logical_switch(self, logical_switch_uuid, ovsdb_identifier,
                              rcv_required=True):
        """Delete an entry from Logical_Switch OVSDB table."""
        commit_dict = {"op": "commit", "durable": True}
        op_id = str(random.getrandbits(128))
        query = {"method": "transact",
                 "params": [n_const.OVSDB_SCHEMA_NAME,
                            {"op": "delete",
                             "table": "Logical_Switch",
                             "where": [["_uuid", "==",
                                        ["uuid", logical_switch_uuid]]]},
                            commit_dict],
                 "id": op_id}
        LOG.debug("delete_logical_switch: query: %s", query)
        self._send_and_receive(query, op_id, ovsdb_identifier, rcv_required)

    def insert_ucast_macs_remote(self, l_switch_dict, locator_dict,
                                 mac_dict, ovsdb_identifier,
                                 rcv_required=True):
        """Insert an entry in Ucast_Macs_Remote OVSDB table."""
        # To insert an entry in Ucast_Macs_Remote table, it requires
        # corresponding entry in Physical_Locator (Compute node VTEP IP)
        # and Logical_Switch (Neutron network) tables.
        logical_switch = ovsdb_schema.LogicalSwitch(l_switch_dict['uuid'],
                                                    l_switch_dict['name'],
                                                    l_switch_dict['key'],
                                                    l_switch_dict['description'
                                                                  ])
        locator = ovsdb_schema.PhysicalLocator(locator_dict['uuid'],
                                               locator_dict['dst_ip'])
        macObject = ovsdb_schema.UcastMacsRemote(mac_dict['uuid'],
                                                 mac_dict['mac'],
                                                 mac_dict['logical_switch_id'],
                                                 mac_dict['physical_locator_id'
                                                          ],
                                                 mac_dict['ip_address'])
        # Form the insert query now.
        commit_dict = {"op": "commit", "durable": True}
        op_id = str(random.getrandbits(128))
        params = [n_const.OVSDB_SCHEMA_NAME]

        if locator.uuid:
            locator_list = ['uuid', locator.uuid]
        else:
            locator.uuid = ''.join(['a', str(random.getrandbits(128))])
            locator_list = ["named-uuid", locator.uuid]
            params.append(self._get_physical_locator_dict(locator))

        if logical_switch.uuid:
            l_switches = ['uuid', logical_switch.uuid]
        else:
            logical_switch.uuid = ''.join(['a', str(random.getrandbits(128))])
            l_switches = ["named-uuid", logical_switch.uuid]
            params.append(self._get_logical_switch_dict(logical_switch))

        params.append(self._get_ucast_macs_remote_dict(
            macObject, locator_list, l_switches))
        params.append(commit_dict)
        query = {"method": "transact",
                 "params": params,
                 "id": op_id}
        LOG.debug("insert_ucast_macs_remote: query: %s", query)
        self._send_and_receive(query, op_id, ovsdb_identifier, rcv_required)

    def update_ucast_macs_remote(self, locator_dict, mac_dict,
                                 ovsdb_identifier,
                                 rcv_required=True):
        """Update an entry in Ucast_Macs_Remote OVSDB table."""
        # It is possible that the locator may not exist already.
        locator = ovsdb_schema.PhysicalLocator(locator_dict['uuid'],
                                               locator_dict['dst_ip'])
        macObject = ovsdb_schema.UcastMacsRemote(mac_dict['uuid'],
                                                 mac_dict['mac'],
                                                 mac_dict['logical_switch_id'],
                                                 mac_dict['physical_locator_id'
                                                          ],
                                                 mac_dict['ip_address'])
        # Form the insert query now.
        commit_dict = {"op": "commit", "durable": True}
        op_id = str(random.getrandbits(128))
        params = [n_const.OVSDB_SCHEMA_NAME]

        # If the physical_locator does not exist (VM moving to a new compute
        # node), then insert a new record in Physical_Locator first.
        if locator.uuid:
            locator_list = ['uuid', locator.uuid]
        else:
            locator.uuid = ''.join(['a', str(random.getrandbits(128))])
            locator_list = ["named-uuid", locator.uuid]
            params.append(self._get_physical_locator_dict(locator))

        params.append(self._get_dict_for_update_ucast_mac_remote(
            macObject, locator_list))
        params.append(commit_dict)
        query = {"method": "transact",
                 "params": params,
                 "id": op_id}
        LOG.debug("update_ucast_macs_remote: query: %s", query)
        self._send_and_receive(query, op_id, ovsdb_identifier, rcv_required)

    def delete_ucast_macs_remote(self, logical_switch_uuid, macs,
                                 ovsdb_identifier,
                                 rcv_required=True):
        """Delete entries from Ucast_Macs_Remote OVSDB table."""
        commit_dict = {"op": "commit", "durable": True}
        op_id = str(random.getrandbits(128))
        params = [n_const.OVSDB_SCHEMA_NAME]
        for mac in macs:
            sub_query = {"op": "delete",
                         "table": "Ucast_Macs_Remote",
                         "where": [["MAC",
                                    "==",
                                    mac],
                                   ["logical_switch",
                                    "==",
                                    ["uuid",
                                     logical_switch_uuid]]]}
            params.append(sub_query)
        params.append(commit_dict)
        query = {"method": "transact",
                 "params": params,
                 "id": op_id}
        LOG.debug("delete_ucast_macs_remote: query: %s", query)
        self._send_and_receive(query, op_id, ovsdb_identifier, rcv_required)

    def update_connection_to_gateway(self, logical_switch_dict,
                                     locator_dicts, mac_dicts,
                                     port_dicts, ovsdb_identifier,
                                     op_method,
                                     rcv_required=True):
        """Updates Physical Port's VNI to VLAN binding."""
        # Form the JSON Query so as to update the physical port with the
        # vni-vlan (logical switch uuid to vlan) binding
        update_dicts = self._get_bindings_to_update(logical_switch_dict,
                                                    locator_dicts,
                                                    mac_dicts,
                                                    port_dicts,
                                                    op_method)
        op_id = str(random.getrandbits(128))
        query = {"method": "transact",
                 "params": update_dicts,
                 "id": op_id}
        LOG.debug("update_connection_to_gateway: query = %s", query)
        self._send_and_receive(query, op_id, ovsdb_identifier, rcv_required)

    def _recv_data(self, ovsdb_identifier):
        chunks = []
        lc = rc = 0
        prev_char = None
        while True:
            try:
                if self.enable_manager:
                    response = self.ovsdb_dicts.get(ovsdb_identifier).recv(
                        n_const.BUFFER_SIZE)
                else:
                    response = self.socket.recv(n_const.BUFFER_SIZE)
                if response:
                    response = response.decode('utf8')
                    for i, c in enumerate(response):
                        if c == '{' and not (prev_char and
                                             prev_char == '\\'):
                            lc += 1
                        elif c == '}' and not (prev_char and
                                               prev_char == '\\'):
                            rc += 1
                        if lc == rc and lc is not 0:
                            chunks.append(response[0:i + 1])
                            message = "".join(chunks)
                            return message
                        prev_char = c
                    chunks.append(response)
                else:
                    LOG.warning("Did not receive any reply from the OVSDB "
                                "server")
                    return
            except (socket.error, socket.timeout):
                LOG.warning("Did not receive any reply from the OVSDB "
                            "server")
                return

    def _get_bindings_to_update(self, l_switch_dict, locator_dicts,
                                mac_dicts, port_dicts, op_method):
        # For connection-create, there are two cases to be handled
        # Case 1: VMs exist in a network on compute nodes.
        #         Connection request will contain locators, ports, MACs and
        #         network.
        # Case 2: VMs do not exist in a network on compute nodes.
        #         Connection request will contain only ports and network
        #
        # For connection-delete, we do not need logical_switch and locators
        # information, we just need ports.
        locator_list = []
        port_list = []
        ls_list = []
        logical_switch = None
        # Convert logical switch dict to a class object
        if l_switch_dict:
            logical_switch = ovsdb_schema.LogicalSwitch(
                l_switch_dict['uuid'],
                l_switch_dict['name'],
                l_switch_dict['key'],
                l_switch_dict['description'])

        # Convert locator dicts into class objects
        for locator in locator_dicts:
            locator_list.append(ovsdb_schema.PhysicalLocator(locator['uuid'],
                                                             locator['dst_ip'])
                                )

        # Convert MAC dicts into class objects. mac_dicts is a dictionary with
        # locator VTEP IP as the key and list of MACs as the value.
        locator_macs = {}
        for locator_ip, mac_list in mac_dicts.items():
            mac_object_list = []
            for mac_dict in mac_list:
                mac_object = ovsdb_schema.UcastMacsRemote(
                    mac_dict['uuid'],
                    mac_dict['mac'],
                    mac_dict['logical_switch_id'],
                    mac_dict['physical_locator_id'],
                    mac_dict['ip_address'])
                mac_object_list.append(mac_object)
            locator_macs[locator_ip] = mac_object_list

        # Convert port dicts into class objects
        for port in port_dicts:
            phys_port = ovsdb_schema.PhysicalPort(port['uuid'],
                                                  port['name'],
                                                  port['physical_switch_id'],
                                                  port['vlan_bindings'],
                                                  port['port_fault_status'])
            port_list.append(phys_port)

        bindings = []
        bindings.append(n_const.OVSDB_SCHEMA_NAME)

        # Form the query.
        commit_dict = {"op": "commit", "durable": True}
        params = [n_const.OVSDB_SCHEMA_NAME]

        # Use logical switch
        if logical_switch:
            ls_list = self._form_logical_switch(logical_switch, params)

        # Use physical locators
        if locator_list:
            self._form_physical_locators(ls_list, locator_list, locator_macs,
                                         params)

        # Use ports
        self._form_ports(ls_list, port_list, params, op_method)
        params.append(commit_dict)
        return params

    def _form_logical_switch(self, logical_switch, params):
        ls_list = []
        if logical_switch.uuid:
            ls_list = ['uuid', logical_switch.uuid]
        else:
            logical_switch.uuid = ''.join(['a', str(random.getrandbits(128))])
            ls_list = ["named-uuid", logical_switch.uuid]
            params.append(self._get_logical_switch_dict(logical_switch))
        return ls_list

    def _form_physical_locators(self, ls_list, locator_list, locator_macs,
                                params):
        for locator in locator_list:
            if locator.uuid:
                loc_list = ['uuid', locator.uuid]
            else:
                locator.uuid = ''.join(['a', str(random.getrandbits(128))])
                loc_list = ["named-uuid", locator.uuid]
                params.append(self._get_physical_locator_dict(locator))
            macs = locator_macs.get(locator.dst_ip, None)
            if macs:
                for mac in macs:
                    query = self._get_ucast_macs_remote_dict(mac,
                                                             loc_list,
                                                             ls_list)
                    params.append(query)

    def _form_ports(self, ls_list, port_list, params, op_method):
        for port in port_list:
            port_vlan_bindings = []
            outer_list = []
            port_vlan_bindings.append("map")
            if port.vlan_bindings:
                for vlan_binding in port.vlan_bindings:
                    if vlan_binding.logical_switch_uuid:
                        outer_list.append([vlan_binding.vlan,
                                          ['uuid',
                                           vlan_binding.logical_switch_uuid]])
                    else:
                        outer_list.append([vlan_binding.vlan,
                                          ls_list])
            port_vlan_bindings.append(outer_list)
            if op_method == 'CREATE':
                update_dict = {"op": "mutate",
                               "table": "Physical_Port",
                               "where": [["_uuid", "==",
                                          ["uuid", port.uuid]]],
                               "mutations": [["vlan_bindings",
                                              "insert",
                                              port_vlan_bindings]]}
            elif op_method == 'DELETE':
                update_dict = {"op": "mutate",
                               "table": "Physical_Port",
                               "where": [["_uuid", "==",
                                         ["uuid", port.uuid]]],
                               "mutations": [["vlan_bindings",
                                              "delete",
                                              port_vlan_bindings]]}
            params.append(update_dict)

    def _get_physical_locator_dict(self, locator):
        return {"op": "insert",
                "table": "Physical_Locator",
                "uuid-name": locator.uuid,
                "row": {"dst_ip": locator.dst_ip,
                        "encapsulation_type": "vxlan_over_ipv4"}}

    def _get_logical_switch_dict(self, logical_switch):
        return {"op": "insert",
                "uuid-name": logical_switch.uuid,
                "table": "Logical_Switch",
                "row": {"description": logical_switch.description,
                        "name": logical_switch.name,
                        "tunnel_key": int(logical_switch.key)}}

    def _get_ucast_macs_remote_dict(self, mac, locator_list,
                                    logical_switch_list):
        named_string = str(random.getrandbits(128))
        return {"op": "insert",
                "uuid-name": ''.join(['a', named_string]),
                "table": "Ucast_Macs_Remote",
                "row": {"MAC": mac.mac,
                        "ipaddr": mac.ip_address,
                        "locator": locator_list,
                        "logical_switch": logical_switch_list}}

    def _get_dict_for_update_ucast_mac_remote(self, mac, locator_list):
        return {"op": "update",
                "table": "Ucast_Macs_Remote",
                "where": [["_uuid", "==",
                           ["uuid", mac.uuid]]],
                "row": {"locator": locator_list}}
