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

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils

from networking_l2gw.services.l2gateway.agent.ovsdb import base_connection
from networking_l2gw.services.l2gateway.common import constants as n_const
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway import exceptions

LOG = logging.getLogger(__name__)


class Activity(object):
    Initial, Update = range(2)


class OVSDBMonitor(base_connection.BaseConnection):
    """Monitors OVSDB servers."""
    def __init__(self, conf, gw_config, callback, mgr=None):
        super(OVSDBMonitor, self).__init__(conf, gw_config, mgr=None)
        self.mgr = mgr
        self.rpc_callback = callback
        self.callbacks = {}
        self._setup_dispatch_table()
        self.read_on = True
        self.handlers = {"echo": self._default_echo_handler}
        self.sock_timeout = cfg.CONF.ovsdb.socket_timeout
        if self.enable_manager:
            self.check_monitor_table_thread = False
        if not self.enable_manager:
            eventlet.greenthread.spawn(self._rcv_thread)

    def _spawn_monitor_table_thread(self, addr):
        self.set_monitor_response_handler(addr)
        self.check_monitor_table_thread = True

    def _initialize_data_dict(self):
        data_dict = {'new_local_macs': [],
                     'deleted_local_macs': [],
                     'modified_local_macs': [],
                     'new_remote_macs': [],
                     'deleted_remote_macs': [],
                     'modified_remote_macs': [],
                     'new_physical_ports': [],
                     'deleted_physical_ports': [],
                     'modified_physical_ports': [],
                     'new_physical_switches': [],
                     'deleted_physical_switches': [],
                     'modified_physical_switches': [],
                     'new_physical_locators': [],
                     'deleted_physical_locators': [],
                     'modified_physical_locators': [],
                     'new_logical_switches': [],
                     'deleted_logical_switches': [],
                     'modified_logical_switches': [],
                     'new_mlocal_macs': [],
                     'deleted_mlocal_macs': [],
                     'modified_mlocal_macs': [],
                     'new_locator_sets': [],
                     'deleted_locator_sets': [],
                     'modified_locator_sets': []}
        return data_dict

    def _setup_dispatch_table(self):
        self.dispatch_table = {'Logical_Switch': self._process_logical_switch,
                               'Ucast_Macs_Local':
                               self._process_ucast_macs_local,
                               'Physical_Locator':
                               self._process_physical_locator,
                               'Ucast_Macs_Remote':
                               self._process_ucast_macs_remote,
                               'Mcast_Macs_Local':
                               self._process_mcast_macs_local,
                               'Physical_Locator_Set':
                               self._process_physical_locator_set
                               }

    def set_monitor_response_handler(self, addr=None):
        """Monitor OVSDB tables to receive events for any changes in OVSDB."""
        if self.connected:
                op_id = str(random.getrandbits(128))
                props = {'select': {'initial': True,
                                    'insert': True,
                                    'delete': True,
                                    'modify': True}}
                monitor_message = {'id': op_id,
                                   'method': 'monitor',
                                   'params': [n_const.OVSDB_SCHEMA_NAME,
                                              None,
                                              {'Logical_Switch': [props],
                                               'Physical_Switch': [props],
                                               'Physical_Port': [props],
                                               'Ucast_Macs_Local': [props],
                                               'Ucast_Macs_Remote': [props],
                                               'Physical_Locator': [props],
                                               'Mcast_Macs_Local': [props],
                                               'Physical_Locator_Set': [props]}
                                              ]}
                self._set_handler("update", self._update_event_handler)
                if not self.send(monitor_message, addr=addr):
                    # Return so that this will retried in the next iteration
                    return
                try:
                    response_result = self._process_response(op_id)
                except exceptions.OVSDBError:
                    with excutils.save_and_reraise_exception():
                        if self.enable_manager:
                            self.check_monitor_table_thread = False
                        LOG.exception("Exception while receiving the "
                                      "response for the monitor message")
                self._process_monitor_msg(response_result, addr)

    def _update_event_handler(self, message, addr):
        self._process_update_event(message, addr)

    def _process_update_event(self, message, addr):
        """Process update event that is triggered by the OVSDB server."""
        LOG.debug("_process_update_event: message = %s ", str(message))
        data_dict = self._initialize_data_dict()
        if message.get('method') == 'update':
            params_list = message.get('params')
            param_dict = params_list[1]
            self._process_tables(param_dict, data_dict)
            self.rpc_callback(Activity.Update,
                              self._form_ovsdb_data(data_dict, addr))

    def _process_tables(self, param_dict, data_dict):
        # Process all the tables one by one.
        # OVSDB table name is the key in the dictionary.
        port_map = {}
        for table_name in param_dict.keys():
            table_dict = param_dict.get(table_name)
            for uuid in table_dict.keys():
                uuid_dict = table_dict.get(uuid)
                if table_name == 'Physical_Switch':
                    self._process_physical_switch(uuid,
                                                  uuid_dict,
                                                  port_map,
                                                  data_dict)
                elif table_name == 'Physical_Port':
                    self._process_physical_port(uuid, uuid_dict,
                                                port_map, data_dict)
                else:
                    self.dispatch_table.get(table_name)(uuid, uuid_dict,
                                                        data_dict)

    def _process_response(self, op_id):
        result = self._response(op_id)
        count = 0
        while (not result and count <= n_const.MAX_RETRIES):
            count = count + 1
            eventlet.greenthread.sleep(0)
            result = self._response(op_id)
        if not result and count >= n_const.MAX_RETRIES:
            raise exceptions.OVSDBError(
                message="OVSDB server did not respond within "
                "max retry attempts.")
        error = result.get("error", None)
        if error:
            raise exceptions.OVSDBError(
                message="Error from the OVSDB server %s" % error
                )
        return result

    def _default_echo_handler(self, message, addr):
        """Message handler for the OVSDB server's echo request."""
        self.send({"result": message.get("params", None),
                   "error": None, "id": message['id']}, addr=addr)

    def _set_handler(self, method_name, handler):
        self.handlers[method_name] = handler

    def _on_remote_message(self, message, addr=None):
        """Processes the message received on the socket."""
        try:
            json_m = jsonutils.loads(message)
            handler_method = json_m.get('method', None)
            if handler_method:
                self.handlers.get(handler_method)(json_m, addr)
            else:
                self.responses.append(json_m)
        except Exception as e:
            LOG.exception("Exception [%s] while handling "
                          "message", e)

    def _rcv_thread(self):
        chunks = []
        lc = rc = 0
        prev_char = None
        while self.read_on:
            try:
                # self.socket.recv() is a blocked call
                # (if timeout value is not passed) due to which we cannot
                # determine if the remote OVSDB server has died. The remote
                # OVSDB server sends echo requests every 4 seconds.
                # If there is no echo request on the socket for socket_timeout
                # seconds(by default its 30 seconds),
                # the agent can safely assume that the connection with the
                # remote OVSDB server is lost. Better to retry by reopening
                # the socket.
                self.socket.settimeout(self.sock_timeout)
                response = self.socket.recv(n_const.BUFFER_SIZE)
                eventlet.greenthread.sleep(0)
                if response:
                    response = response.decode('utf8')
                    message_mark = 0
                    for i, c in enumerate(response):
                        if c == '{' and not (prev_char and
                                             prev_char == '\\'):
                            lc += 1
                        elif c == '}' and not (prev_char and
                                               prev_char == '\\'):
                            rc += 1
                        if rc > lc:
                            raise Exception("json string not valid")
                        elif lc == rc and lc is not 0:
                            chunks.append(response[message_mark:i + 1])
                            message = "".join(chunks)
                            eventlet.greenthread.spawn_n(
                                self._on_remote_message, message)
                            lc = rc = 0
                            message_mark = i + 1
                            chunks = []
                        prev_char = c
                    chunks.append(response[message_mark:])
                else:
                    self.read_on = False
                    self.disconnect()
            except Exception as ex:
                self.read_on = False
                self.disconnect()
                LOG.exception("Exception [%s] occurred while receiving"
                              "message from the OVSDB server", ex)

    def disconnect(self, addr=None):
        """disconnects the connection from the OVSDB server."""
        self.read_on = False
        super(OVSDBMonitor, self).disconnect(addr)

    def _process_monitor_msg(self, message, addr=None):
        """Process initial set of records in the OVSDB at startup."""
        result_dict = message.get('result')
        data_dict = self._initialize_data_dict()
        try:
            self._process_tables(result_dict, data_dict)
            self.rpc_callback(Activity.Initial,
                              self._form_ovsdb_data(data_dict, addr))
        except Exception as e:
            LOG.exception("_process_monitor_msg:ERROR %s ", e)

    def _get_list(self, resource_list):
        return [element.__dict__ for element in resource_list]

    def _form_ovsdb_data(self, data_dict, addr):
        return {n_const.OVSDB_IDENTIFIER: str(addr) if (
                self.enable_manager) else (self.gw_config.ovsdb_identifier),
                'new_logical_switches': self._get_list(
                    data_dict.get('new_logical_switches')),
                'new_physical_switches': self._get_list(
                    data_dict.get('new_physical_switches')),
                'new_physical_ports': self._get_list(
                    data_dict.get('new_physical_ports')),
                'new_physical_locators': self._get_list(
                    data_dict.get('new_physical_locators')),
                'new_local_macs': self._get_list(
                    data_dict.get('new_local_macs')),
                'new_remote_macs': self._get_list(
                    data_dict.get('new_remote_macs')),
                'new_mlocal_macs': self._get_list(
                    data_dict.get('new_mlocal_macs')),
                'new_locator_sets': self._get_list(
                    data_dict.get('new_locator_sets')),
                'deleted_logical_switches': self._get_list(
                    data_dict.get('deleted_logical_switches')),
                'deleted_physical_switches': self._get_list(
                    data_dict.get('deleted_physical_switches')),
                'deleted_physical_ports': self._get_list(
                    data_dict.get('deleted_physical_ports')),
                'deleted_physical_locators': self._get_list(
                    data_dict.get('deleted_physical_locators')),
                'deleted_local_macs': self._get_list(
                    data_dict.get('deleted_local_macs')),
                'deleted_remote_macs': self._get_list(
                    data_dict.get('deleted_remote_macs')),
                'deleted_mlocal_macs': self._get_list(
                    data_dict.get('deleted_mlocal_macs')),
                'deleted_locator_sets': self._get_list(
                    data_dict.get('deleted_locator_sets')),
                'modified_logical_switches': self._get_list(
                    data_dict.get('modified_logical_switches')),
                'modified_physical_switches': self._get_list(
                    data_dict.get('modified_physical_switches')),
                'modified_physical_ports': self._get_list(
                    data_dict.get('modified_physical_ports')),
                'modified_physical_locators': self._get_list(
                    data_dict.get('modified_physical_locators')),
                'modified_local_macs': self._get_list(
                    data_dict.get('modified_local_macs')),
                'modified_remote_macs': self._get_list(
                    data_dict.get('modified_remote_macs')),
                'modified_mlocal_macs': self._get_list(
                    data_dict.get('modified_mlocal_macs')),
                'modified_locator_sets': self._get_list(
                    data_dict.get('modified_locator_sets'))}

    def _process_physical_port(self, uuid, uuid_dict, port_map, data_dict):
        """Processes Physical_Port record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            port_fault_status = new_row.get('port_fault_status')
            if type(port_fault_status) is list:
                port_fault_status = None
            port = ovsdb_schema.PhysicalPort(uuid, new_row.get('name'), None,
                                             None,
                                             port_fault_status)
            switch_id = port_map.get(uuid, None)
            if switch_id:
                port.physical_switch_id = switch_id
            # Update the vlan bindings
            outer_binding_list = new_row.get('vlan_bindings')
            # First element is "map"
            outer_binding_list.remove(outer_binding_list[0])
            vlan_bindings = []
            if len(outer_binding_list) > 0:
                for binding in outer_binding_list:
                    if len(binding) > 0:
                        for element in binding:
                            vlan = element[0]
                            inner_most_list = element[1]
                            ls_id = inner_most_list[1]
                            vb = ovsdb_schema.VlanBinding(vlan, ls_id).__dict__
                            vlan_bindings.append(vb)
            port.vlan_bindings = vlan_bindings
            if old_row:
                modified_physical_ports = data_dict.get(
                    'modified_physical_ports')
                modified_physical_ports.append(port)
            else:
                new_physical_ports = data_dict.get(
                    'new_physical_ports')
                new_physical_ports.append(port)
        elif old_row:
            # Port is deleted permanently from OVSDB server
            port_fault_status = old_row.get('port_fault_status')
            if type(port_fault_status) is list:
                port_fault_status = None
            port = ovsdb_schema.PhysicalPort(uuid, old_row.get('name'), None,
                                             None,
                                             port_fault_status)
            deleted_physical_ports = data_dict.get('deleted_physical_ports')
            deleted_physical_ports.append(port)

    def _process_physical_switch(self, uuid, uuid_dict, port_map, data_dict):
        """Processes Physical_Switch record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            # insert or modify operation
            ports = new_row.get('ports')
            # First element in the list is either 'set' or 'uuid'
            # Let us remove it.
            is_set = False
            if ports[0] == 'set':
                is_set = True
            ports.remove(ports[0])
            all_ports = []
            if not is_set:
                all_ports.append(ports[0])
            else:
                for port_list in ports:
                    # each port variable is again list
                    for port in port_list:
                        for inner_port in port:
                            if inner_port != 'uuid':
                                all_ports.append(inner_port)
            switch_fault_status = new_row.get('switch_fault_status')
            if type(switch_fault_status) is list:
                switch_fault_status = None
            phys_switch = ovsdb_schema.PhysicalSwitch(
                uuid, new_row.get('name'), new_row.get('tunnel_ips'),
                switch_fault_status)
            # Now, store mapping of physical ports to
            # physical switch so that it is useful while
            # processing Physical_Switch record
            for port in all_ports:
                port_map[port] = uuid
                for pport in data_dict['new_physical_ports']:
                    if pport.uuid == port:
                        pport.physical_switch_id = uuid
            if old_row:
                modified_physical_switches = data_dict.get(
                    'modified_physical_switches')
                modified_physical_switches.append(phys_switch)
            else:
                new_physical_switches = data_dict.get(
                    'new_physical_switches')
                new_physical_switches.append(phys_switch)
        elif old_row:
            # Physical switch is deleted permanently from OVSDB
            # server
            switch_fault_status = old_row.get('switch_fault_status')
            if type(switch_fault_status) is list:
                switch_fault_status = None
            phys_switch = ovsdb_schema.PhysicalSwitch(
                uuid, old_row.get('name'), old_row.get('tunnel_ips'),
                switch_fault_status)
            deleted_physical_switches = data_dict.get(
                'deleted_physical_switches')
            deleted_physical_switches.append(phys_switch)

    def _process_logical_switch(self, uuid, uuid_dict, data_dict):
        """Processes Logical_Switch record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            l_switch = ovsdb_schema.LogicalSwitch(uuid,
                                                  new_row.get('name'),
                                                  new_row.get('tunnel_key'),
                                                  new_row.get('description'))
            if old_row:
                modified_logical_switches = data_dict.get(
                    'modified_logical_switches')
                modified_logical_switches.append(l_switch)
            else:
                new_logical_switches = data_dict.get(
                    'new_logical_switches')
                new_logical_switches.append(l_switch)
        elif old_row:
            l_switch = ovsdb_schema.LogicalSwitch(uuid,
                                                  old_row.get('name'),
                                                  old_row.get('tunnel_key'),
                                                  old_row.get('description'))
            deleted_logical_switches = data_dict.get(
                'deleted_logical_switches')
            deleted_logical_switches.append(l_switch)

    def _process_ucast_macs_local(self, uuid, uuid_dict, data_dict):
        """Processes Ucast_Macs_Local record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            locator_list = new_row.get('locator')
            locator_id = locator_list[1]
            logical_switch_list = new_row.get('logical_switch')
            logical_switch_id = logical_switch_list[1]
            mac_local = ovsdb_schema.UcastMacsLocal(uuid,
                                                    new_row.get('MAC'),
                                                    logical_switch_id,
                                                    locator_id,
                                                    new_row.get('ipaddr'))
            if old_row:
                modified_local_macs = data_dict.get(
                    'modified_local_macs')
                modified_local_macs.append(mac_local)
            else:
                new_local_macs = data_dict.get(
                    'new_local_macs')
                new_local_macs.append(mac_local)
        elif old_row:
            # A row from UcastMacLocal is deleted.
            logical_switch_list = old_row.get('logical_switch')
            l_sw_id = logical_switch_list[1]
            mac_local = ovsdb_schema.UcastMacsLocal(uuid,
                                                    old_row.get('MAC'),
                                                    l_sw_id,
                                                    None,
                                                    None)
            deleted_local_macs = data_dict.get(
                'deleted_local_macs')
            deleted_local_macs.append(mac_local)

    def _process_ucast_macs_remote(self, uuid, uuid_dict, data_dict):
        """Processes Ucast_Macs_Remote record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            locator_list = new_row.get('locator')
            locator_id = locator_list[1]
            logical_switch_list = new_row.get('logical_switch')
            logical_switch_id = logical_switch_list[1]
            mac_remote = ovsdb_schema.UcastMacsRemote(uuid,
                                                      new_row.get('MAC'),
                                                      logical_switch_id,
                                                      locator_id,
                                                      new_row.get('ipaddr'))
            if old_row:
                modified_remote_macs = data_dict.get(
                    'modified_remote_macs')
                modified_remote_macs.append(mac_remote)
            else:
                new_remote_macs = data_dict.get(
                    'new_remote_macs')
                new_remote_macs.append(mac_remote)
        elif old_row:
            logical_switch_list = old_row.get('logical_switch')
            l_sw_id = logical_switch_list[1]
            mac_remote = ovsdb_schema.UcastMacsRemote(uuid,
                                                      old_row.get('MAC'),
                                                      l_sw_id,
                                                      None,
                                                      None)
            deleted_remote_macs = data_dict.get(
                'deleted_remote_macs')
            deleted_remote_macs.append(mac_remote)

    def _process_physical_locator(self, uuid, uuid_dict, data_dict):
        """Processes Physical_Locator record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            dstip = new_row['dst_ip']
            locator = ovsdb_schema.PhysicalLocator(uuid, dstip)
            if old_row:
                modified_physical_locators = data_dict.get(
                    'modified_physical_locators')
                modified_physical_locators.append(locator)
            else:
                new_physical_locators = data_dict.get(
                    'new_physical_locators')
                new_physical_locators.append(locator)
        elif old_row:
            dstip = old_row['dst_ip']
            locator = ovsdb_schema.PhysicalLocator(uuid, dstip)
            deleted_physical_locators = data_dict.get(
                'deleted_physical_locators')
            deleted_physical_locators.append(locator)

    def _process_mcast_macs_local(self, uuid, uuid_dict, data_dict):
        """Processes Mcast_Macs_Local record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            locator_set_list = new_row.get('locator_set')
            logical_switch_list = new_row.get('logical_switch')
            mcast_local = ovsdb_schema.McastMacsLocal(uuid,
                                                      new_row['MAC'],
                                                      logical_switch_list[1],
                                                      locator_set_list[1],
                                                      new_row['ipaddr'])
            if old_row:
                modified_mlocal_macs = data_dict.get(
                    'modified_mlocal_macs')
                modified_mlocal_macs.append(mcast_local)
            else:
                new_mlocal_macs = data_dict.get(
                    'new_mlocal_macs')
                new_mlocal_macs.append(mcast_local)
        elif old_row:
            logical_switch_list = old_row.get('logical_switch')
            l_sw_id = logical_switch_list[1]
            mcast_local = ovsdb_schema.McastMacsLocal(uuid,
                                                      old_row.get('MAC'),
                                                      l_sw_id,
                                                      None,
                                                      None)
            deleted_mlocal_macs = data_dict.get(
                'deleted_mlocal_macs')
            deleted_mlocal_macs.append(mcast_local)

    def _process_physical_locator_set(self, uuid, uuid_dict, data_dict):
        """Processes Physical_Locator_Set record from the OVSDB event."""
        new_row = uuid_dict.get('new', None)
        old_row = uuid_dict.get('old', None)
        if new_row:
            locator_set = self._form_locator_set(uuid, new_row)
            if old_row:
                modified_locator_sets = data_dict.get(
                    'modified_locator_sets')
                modified_locator_sets.append(locator_set)
            else:
                new_locator_sets = data_dict.get(
                    'new_locator_sets')
                new_locator_sets.append(locator_set)
        elif old_row:
            locator_set = self._form_locator_set(uuid, old_row)
            deleted_locator_sets = data_dict.get(
                'deleted_locator_sets')
            deleted_locator_sets.append(locator_set)

    def _form_locator_set(self, uuid, row):
        locators = []
        locator_set_list = row.get('locators')
        if locator_set_list[0] == 'set':
            locator_set_list = locator_set_list[1]
            for locator in locator_set_list:
                locators.append(locator[1])
        else:
            locators.append(locator_set_list[1])
        locator_set = ovsdb_schema.PhysicalLocatorSet(uuid,
                                                      locators)
        return locator_set
