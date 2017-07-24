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

import abc

from neutron.common import constants as nc_const
from neutron.common import rpc as n_rpc
from neutron.db import agents_db

from networking_l2gw._i18n import _
from networking_l2gw.db.l2gateway import l2gateway_db as l2_gw_db
from networking_l2gw.db.l2gateway.ovsdb import lib as db
from networking_l2gw.services.l2gateway import agent_scheduler
from networking_l2gw.services.l2gateway.common import constants
from networking_l2gw.services.l2gateway.common import l2gw_validators
from networking_l2gw.services.l2gateway.common import ovsdb_schema
from networking_l2gw.services.l2gateway.common import topics
from networking_l2gw.services.l2gateway import exceptions as l2gw_exc
from networking_l2gw.services.l2gateway import service_drivers
from networking_l2gw.services.l2gateway.service_drivers import agent_api

from neutron.plugins.ml2 import managers

from neutron_lib.api.definitions import portbindings
from neutron_lib import constants as n_const
from neutron_lib import exceptions
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import importutils
import six

LOG = logging.getLogger(__name__)

L2GW = 'l2gw'
L2GW_CALLBACK = ("networking_l2gw.services.l2gateway.ovsdb."
                 "data.L2GatewayOVSDBCallbacks")


@six.add_metaclass(abc.ABCMeta)
class L2gwRpcDriver(service_drivers.L2gwDriver):
    """L2gw RPC Service Driver class."""

    def __init__(self, service_plugin, validator=None):
        super(L2gwRpcDriver, self).__init__(service_plugin, validator)
        self.ovsdb_callback = importutils.import_object(
            L2GW_CALLBACK, self)
        self.endpoints = (
            [self.ovsdb_callback, agents_db.AgentExtRpcCallback()])
        self.conn = n_rpc.create_connection()
        self.conn.create_consumer(topics.L2GATEWAY_PLUGIN,
                                  self.endpoints,
                                  fanout=False)
        self.conn.consume_in_threads()
        self.create_rpc_conn()
        LOG.debug("starting l2gateway agent scheduler")
        self.start_l2gateway_agent_scheduler()
        self.gateway_resource = constants.GATEWAY_RESOURCE_NAME
        self.l2gateway_db = l2_gw_db.L2GatewayMixin()
        self.type_manager = managers.TypeManager()

    @property
    def service_type(self):
        return L2GW

    def create_rpc_conn(self):
        self.agent_rpc = agent_api.L2gatewayAgentApi(topics.L2GATEWAY_AGENT,
                                                     cfg.CONF.host)

    def start_l2gateway_agent_scheduler(self):
        """Start l2gateway agent scheduler thread."""
        self.agentscheduler = agent_scheduler.L2GatewayAgentScheduler(
            self.agent_rpc)
        self.agentscheduler.initialize_thread()

    def _get_dict(self, resource):
        return resource.__dict__

    def add_port_mac(self, context, port_dict):
        """Process the created port and trigger the RPC

        to add to the gateway.
        """
        port_id = port_dict.get("id")
        port = self.service_plugin._core_plugin.get_port(context, port_id)
        if port['device_owner']:
            network_id = port.get("network_id")
            dst_ip, ip_address = self._get_ip_details(context, port)
            network = self._get_network_details(context, network_id)
            l2gateway_connections = (
                self.service_plugin.get_l2_gateway_connections(
                    context, filters={'network_id': [network_id]}))
            if not l2gateway_connections:
                return
            logical_switches = db.get_all_logical_switches_by_name(context,
                                                                   network_id)
            if not logical_switches:
                return
            for logical_switch in logical_switches:
                logical_switch['description'] = network.get('name')
                ovsdb_identifier = logical_switch.get('ovsdb_identifier')
                locator_dict = {'dst_ip': dst_ip,
                                'ovsdb_identifier': ovsdb_identifier}
                physical_locator = self._form_physical_locator_schema(
                    context, locator_dict)
                locator_uuid = physical_locator.get('uuid')
                logical_switch_uuid = logical_switch.get('uuid')
                mac_remote = self._get_dict(ovsdb_schema.UcastMacsRemote(
                    uuid=None,
                    mac=port['mac_address'],
                    logical_switch_id=logical_switch_uuid,
                    physical_locator_id=locator_uuid,
                    ip_address=ip_address))
                mac_dict = mac_remote
                mac_dict['ovsdb_identifier'] = ovsdb_identifier
                mac_dict['logical_switch_uuid'] = logical_switch_uuid
                ucast_mac_remote = db.get_ucast_mac_remote_by_mac_and_ls(
                    context, mac_dict)
                if ucast_mac_remote:
                    # check whether locator got changed in vm migration
                    if ucast_mac_remote['physical_locator_id'
                                        ] != physical_locator['uuid']:
                        mac_remote['uuid'] = ucast_mac_remote['uuid']
                        try:
                            self.agent_rpc.update_vif_to_gateway(
                                context, ovsdb_identifier,
                                physical_locator, mac_remote)
                            LOG.debug(
                                "VM migrated from %s to %s. Update"
                                "locator in Ucast_Macs_Remote",
                                ucast_mac_remote['physical_locator_id'],
                                physical_locator['uuid'])
                        except messaging.MessagingTimeout:
                            # If RPC is timed out, then the RabbitMQ
                            # will retry the operation.
                            LOG.exception("Communication error with "
                                          "the L2 gateway agent")
                        except Exception:
                            # The remote OVSDB server may be down.
                            # We need to retry this operation later.
                            db.add_pending_ucast_mac_remote(
                                context, 'update',
                                ovsdb_identifier,
                                logical_switch_uuid,
                                physical_locator,
                                [mac_remote])
                    else:
                        LOG.debug("add_port_mac: MAC %s exists "
                                  "in Gateway", mac_dict['mac'])
                        ovsdb_data_handler = (
                            self.ovsdb_callback.get_ovsdbdata_object(
                                ovsdb_identifier))
                        ovsdb_data_handler._handle_l2pop(
                            context, [ucast_mac_remote])
                    continue
                # else it is a new port created
                try:
                    self.agent_rpc.add_vif_to_gateway(
                        context, ovsdb_identifier, logical_switch,
                        physical_locator, mac_remote)
                except messaging.MessagingTimeout:
                    # If RPC is timed out, then the RabbitMQ
                    # will retry the operation.
                    LOG.exception("Communication error with "
                                  "the L2 gateway agent")
                except Exception:
                    # The remote OVSDB server may be down.
                    # We need to retry this operation later.
                    LOG.debug("The remote OVSDB server may be down")
                    db.add_pending_ucast_mac_remote(
                        context, 'insert', ovsdb_identifier,
                        logical_switch_uuid,
                        physical_locator,
                        [mac_remote])

    def _form_physical_locator_schema(self, context, pl_dict):
        locator_uuid = None
        locator = db.get_physical_locator_by_dst_ip(
            context, pl_dict)
        if locator:
            locator_uuid = locator.get('uuid')
        physical_locator = self._get_dict(
            ovsdb_schema.PhysicalLocator(uuid=locator_uuid,
                                         dst_ip=pl_dict.get('dst_ip')))
        return physical_locator

    def delete_port_mac(self, context, port):
        """Process the deleted port and trigger the RPC

        to delete from the gateway.

        When the ML2 plugin invokes this call, the argument port is
        a single port dict, whereas the L2gateway service plugin
        sends it as a list of port dicts.
        """
        ls_dict = {}
        mac_list = []
        logical_switches = []
        ovsdb_identifier = None
        if isinstance(port, list):
            from_l2gw_plugin = True
            network_id = port[0].get('network_id')
            ovsdb_identifier = port[0].get('ovsdb_identifier')
            lg_dict = {'logical_switch_name': network_id,
                       'ovsdb_identifier': ovsdb_identifier}
            logical_switch = db.get_logical_switch_by_name(
                context, lg_dict)
            logical_switches.append(logical_switch)
            port_list = port
        else:
            from_l2gw_plugin = False
            network_id = port.get('network_id')
            logical_switches = (
                db.get_all_logical_switches_by_name(
                    context, network_id))
            l2gateway_connections = (
                self.service_plugin.get_l2_gateway_connections(
                    context, filters={'network_id': [network_id]}))
            if not l2gateway_connections:
                return
            port_list = [port]
        for port_dict in port_list:
            if port_dict['device_owner']:
                if logical_switches:
                    for logical_switch in logical_switches:
                        logical_switch_uuid = logical_switch.get('uuid')
                        macs = []
                        if isinstance(port_dict.get("allowed_address_pairs"),
                                      list):
                            for address_pair in port_dict[
                                    'allowed_address_pairs']:
                                mac = address_pair['mac_address']
                                macs.append(mac)
                        macs.append(port_dict.get("mac_address"))
                        if port_dict.get('ovsdb_identifier', None):
                            ovsdb_identifier = port_dict.get(
                                'ovsdb_identifier')
                        else:
                            ovsdb_identifier = logical_switch.get(
                                'ovsdb_identifier')

                        if from_l2gw_plugin:
                            ls = logical_switch.get('name')
                            l2gateway_connections = (
                                self.service_plugin.
                                get_l2_gateway_connections(
                                    context,
                                    filters={'network_id': [ls]}))
                            if len(l2gateway_connections) > 1:
                                continue
                        for mac in macs:
                            record_dict = {'mac': mac,
                                           'logical_switch_uuid':
                                           logical_switch_uuid,
                                           'ovsdb_identifier':
                                           ovsdb_identifier}

                            ucast_mac_remote = (
                                db.get_ucast_mac_remote_by_mac_and_ls(
                                    context, record_dict))
                            del_count = 0
                            if not ucast_mac_remote:
                                LOG.debug("delete_port_mac: MAC %s does"
                                          " not exist", mac)
                                # It is possible that this MAC is present
                                # in the pending_ucast_mac_remote table.
                                # Delete this MAC as it was not inserted
                                # into the OVSDB server earlier.
                                del_count = db.delete_pending_ucast_mac_remote(
                                    context, 'insert',
                                    ovsdb_identifier,
                                    logical_switch_uuid,
                                    mac)
                            if not del_count:
                                mac_list = ls_dict.get(logical_switch_uuid, [])
                                mac_list.append(mac)
                                ls_dict[logical_switch_uuid] = mac_list
                else:
                    LOG.debug("delete_port_mac:Logical Switch %s "
                              "does not exist ", port_dict.get('network_id'))
                    return
        for logical_switch_uuid, mac_list in ls_dict.items():
            try:
                if mac_list:
                    self.agent_rpc.delete_vif_from_gateway(context,
                                                           ovsdb_identifier,
                                                           logical_switch_uuid,
                                                           mac_list)
            except messaging.MessagingTimeout:
                # If RPC is timed out, then the RabbitMQ
                # will retry the operation.
                LOG.exception("Communication error with "
                              "the L2 gateway agent")
            except Exception as ex:
                # The remote OVSDB server may be down.
                # We need to retry this operation later.
                LOG.debug("Exception occurred %s", str(ex))
                db.add_pending_ucast_mac_remote(
                    context, 'delete', ovsdb_identifier,
                    logical_switch_uuid,
                    None,
                    mac_list)

    def _check_port_fault_status_and_switch_fault_status(self, context,
                                                         l2_gateway_id):
        l2gw = self.service_plugin.get_l2_gateway(context, l2_gateway_id)
        if not l2gw:
            raise l2gw_exc.L2GatewayNotFound(gateway_id=l2_gateway_id)
        devices = l2gw['devices']
        rec_dict = {}
        for device in devices:
            device_name = device['device_name']
            dev_db = db.get_physical_switch_by_name(context, device_name)
            if not dev_db:
                raise l2gw_exc.L2GatewayDeviceNotFound(device_id=device_name)
            rec_dict['physical_switch_id'] = dev_db['uuid']
            rec_dict['ovsdb_identifier'] = dev_db['ovsdb_identifier']
            status = dev_db.get('switch_fault_status')
            if status and status != constants.SWITCH_FAULT_STATUS_UP:
                raise l2gw_exc.L2GatewayPhysicalSwitchFaultStatus(
                    device_name=device_name, fault_status=status)
            for interface_list in device['interfaces']:
                int_name = interface_list.get('name')
                rec_dict['interface_name'] = int_name
                port_db = db.get_physical_port_by_name_and_ps(context,
                                                              rec_dict)
                if not port_db:
                    raise l2gw_exc.L2GatewayInterfaceNotFound(
                        interface_id=int_name)

                port_status = port_db['port_fault_status']
                if (port_status and port_status !=
                        constants.PORT_FAULT_STATUS_UP):
                    raise l2gw_exc.L2GatewayPhysicalPortFaultStatus(
                        int_name=int_name, device_name=device_name,
                        fault_status=port_status)

    def _validate_connection(self, context, gw_connection):
        seg_id = gw_connection.get('segmentation_id', None)
        l2_gw_id = gw_connection.get('l2_gateway_id')
        self._check_port_fault_status_and_switch_fault_status(context,
                                                              l2_gw_id)
        check_vlan = (
            self.service_plugin._is_vlan_configured_on_any_interface_for_l2gw(
                context, l2_gw_id))
        nw_map = {}
        network_id = gw_connection.get(constants.NETWORK_ID)
        nw_map[constants.NETWORK_ID] = network_id
        nw_map['l2_gateway_id'] = l2_gw_id
        if seg_id:
            nw_map[constants.SEG_ID] = gw_connection.get(constants.SEG_ID)
        if not self.service_plugin._get_network(context, network_id):
            raise exceptions.NetworkNotFound(net_id=network_id)
        if self.service_plugin._retrieve_gateway_connections(context,
                                                             l2_gw_id, nw_map):
            raise l2gw_exc.L2GatewayConnectionExists(mapping=nw_map,
                                                     gateway_id=l2_gw_id)
        l2gw_validators.validate_network_mapping_list(nw_map, check_vlan)
        gw_db = self.service_plugin._get_l2_gateway(context, l2_gw_id)
        tenant_id = self.service_plugin._get_tenant_id_for_create(
            context, gw_db)
        l2gw_connection = self.service_plugin.get_l2_gateway_connections(
            context, filters={'network_id': [network_id],
                              'tenant_id': [tenant_id],
                              'l2_gateway_id': [l2_gw_id]})
        if l2gw_connection:
            raise l2gw_exc.L2GatewayConnectionExists(mapping=nw_map,
                                                     gateway_id=l2_gw_id)

    def _process_port_list(self, context, device,
                           gw_connection, method,
                           gw_connection_ovsdb_set=None):
        port_dicts = []
        port_dict = {}
        logical_switch_uuid = None
        seg_id = gw_connection.get('segmentation_id', None)
        interfaces = self.service_plugin.get_l2gateway_interfaces_by_device_id(
            context, device['id'])
        for interface in interfaces:
            interface_name = interface.get('interface_name')
            physical_switch = db.get_physical_switch_by_name(
                context, device.get('device_name'))
            if not physical_switch:
                msg = _('The PHYSICAL SWITCH data not found in the server')
                raise Exception(msg)
            ovsdb_identifier = physical_switch.get('ovsdb_identifier')
            pp_dict = {'interface_name': interface_name,
                       'ovsdb_identifier': ovsdb_identifier,
                       'physical_switch_id': physical_switch.get('uuid'),
                       'logical_switch_name': gw_connection.get(
                           'network_id')}
            logical_switch = db.get_logical_switch_by_name(
                context, pp_dict)
            if method == "DELETE":
                if not logical_switch:
                    msg = _('The LOGICAL SWITCH data not found in the server')
                    raise Exception(msg)
                if not (ovsdb_identifier in list(gw_connection_ovsdb_set)):
                    continue
            if logical_switch:
                logical_switch_uuid = logical_switch.get('uuid')
            ps_port = db.get_physical_port_by_name_and_ps(context, pp_dict)
            if not ps_port:
                msg = _('The PHYSICAL PORT data not found in the server')
                raise Exception(msg)
            pp_dict['uuid'] = ps_port.get('uuid')
            pp_dict['name'] = ps_port.get('name')
            port_dict = self._generate_port_list(
                context, method, seg_id, interface, pp_dict,
                logical_switch_uuid, gw_connection)
            port_dicts.append(port_dict)
        return ovsdb_identifier, logical_switch, port_dicts

    def _generate_port_list(self, context, method, seg_id,
                            interface, pp_dict,
                            logical_switch_uuid, gw_connection=None):
        port_list = []
        vlan_bindings = db.get_all_vlan_bindings_by_physical_port(
            context, pp_dict)
        if method == "CREATE":
            if not seg_id:
                vlan_id = interface.get('segmentation_id')
            else:
                vlan_id = int(seg_id)
            vlan_dict = {'vlan': vlan_id,
                         'logical_switch_uuid': logical_switch_uuid}
            port_list.append(vlan_dict)
            for vlan_binding in vlan_bindings:
                if vlan_binding.get('vlan') == vlan_id:
                    msg = _('Duplicate segmentation ID for the interface '
                            'name=%(name)s uuid=%(uuid)s'
                            ) % {'name': pp_dict['name'],
                                 'uuid': pp_dict['uuid']}
                    raise l2gw_exc.L2GatewayDuplicateSegmentationID(message=msg
                                                                    )
            physical_port = self._get_dict(
                ovsdb_schema.PhysicalPort(
                    uuid=pp_dict.get('uuid'),
                    name=pp_dict.get('interface_name'),
                    phys_switch_id=pp_dict.get('physical_switch_id'),
                    vlan_binding_dicts=None,
                    port_fault_status=None))
            physical_port['vlan_bindings'] = port_list
        else:
            vlan_id = gw_connection.get('segmentation_id')
            if not vlan_id:
                vlan_id = interface.get('segmentation_id')
            vlan_dict = {'vlan': vlan_id,
                         'logical_switch_uuid': logical_switch_uuid}
            port_list.append(vlan_dict)
            physical_port = self._get_dict(
                ovsdb_schema.PhysicalPort(
                    uuid=pp_dict.get('uuid'),
                    name=pp_dict.get('interface_name'),
                    phys_switch_id=pp_dict.get('physical_switch_id'),
                    vlan_binding_dicts=None,
                    port_fault_status=None))
            physical_port['vlan_bindings'] = port_list
        return physical_port

    def _get_ip_details(self, context, port):
        host = port[portbindings.HOST_ID]
        if (not host and
                (port['device_owner'] == n_const.DEVICE_OWNER_DVR_INTERFACE)):
            return self._get_l3_dvr_agent_details(context, port)
        agent = self._get_agent_details(context, host)
        conf_dict = agent.get("configurations")
        dst_ip = conf_dict.get("tunneling_ip")
        fixed_ip_list = port.get('fixed_ips')
        fixed_ip_list = fixed_ip_list[0]
        return dst_ip, fixed_ip_list.get('ip_address')

    def _get_network_details(self, context, network_id):
        network = self.service_plugin._core_plugin.get_network(context,
                                                               network_id)
        return network

    def _get_port_details(self, context, network_id):
        ports = self.service_plugin._core_plugin.get_ports(
            context, filters={'network_id': [network_id]})
        return ports

    def _get_agent_details(self, context, host):
        l2_agent = None
        agents = self.service_plugin._core_plugin.get_agents(
            context, filters={'host': [host]})
        for agent in agents:
            agent_tunnel_type = agent['configurations'].get('tunnel_types', [])
            if constants.VXLAN in agent_tunnel_type:
                l2_agent = agent
                break
        if not l2_agent:
            raise l2gw_exc.L2AgentNotFoundByHost(
                host=host)
        return l2_agent

    def _get_l3_dvr_agent_details(self, context, port):
        """Getting host IP for router port in DVR mode

        in case of DVR, the router port will not have host information as
        there is router in each Compute Node and in the Network Node.
        Here we look for the L3 Agent in the Network Node, get its hostname and
        resolve its hostname to IP address to be used as destination IP.
        """
        endpoints = self.type_manager.drivers.get('vxlan').obj.get_endpoints()
        agents = self.service_plugin._core_plugin.get_agents(
            context,
            filters={
                'agent_type': [n_const.AGENT_TYPE_L3],
                'alive': ['true']
            })
        for agent in agents:
            conf_dict = agent.get("configurations")
            if conf_dict.get("agent_mode") == nc_const.L3_AGENT_MODE_DVR_SNAT:
                hostname = agent.get('host')
                for endpoint in endpoints:
                    if endpoint.get('host') == hostname:
                        dst_ip = endpoint.get('ip_address')
                        fixed_ip_list = port.get('fixed_ips')
                        fixed_ip = fixed_ip_list[0].get('ip_address')
                        LOG.debug(
                            'Adding DVR dst_ip: %s, fixed_ip: %s',
                            dst_ip,
                            fixed_ip
                        )
                        return dst_ip, fixed_ip
                raise l2gw_exc.DvrAgentHostnameNotFound(host=hostname)
        raise l2gw_exc.L3DvrAgentNotFound()

    def _get_logical_switch_dict(self, context, logical_switch, gw_connection):
        if logical_switch:
            uuid = logical_switch.get('uuid')
        else:
            uuid = None
        network_id = gw_connection.get('network_id')
        ls_dict = {'uuid': uuid,
                   'name': network_id}
        network = self._get_network_details(context,
                                            network_id)
        ls_dict['description'] = network.get('name')
        logical_segments = network.get('segments')
        if logical_segments:
            vxlan_seg_id = None
            for seg in logical_segments:
                if seg.get('provider:network_type') == constants.VXLAN:
                    if vxlan_seg_id:
                        raise l2gw_exc.MultipleVxlanSegmentsFound(
                            network_id=network_id)
                    vxlan_seg_id = seg.get('provider:segmentation_id')
                    ls_dict['key'] = vxlan_seg_id
            if not vxlan_seg_id:
                raise l2gw_exc.VxlanSegmentationIDNotFound(
                    network_id=network_id)
        elif network.get('provider:network_type') == constants.VXLAN:
            ls_dict['key'] = network.get('provider:segmentation_id')
        else:
            raise l2gw_exc.VxlanSegmentationIDNotFound(network_id=network_id)
        return ls_dict

    def _get_physical_locator_dict(self, dst_ip,
                                   uuid=None, macs=None,
                                   ovsdb_identifier=None):
        pl_dict = {'uuid': uuid,
                   'dst_ip': dst_ip,
                   'ovsdb_identifier': ovsdb_identifier}
        if macs:
            pl_dict['macs'] = macs
        else:
            pl_dict['macs'] = []
        return pl_dict

    def _get_locator_list(self, context, dst_ip, ovsdb_identifier,
                          mac_list, locator_list):
        locator_uuid = None
        locator_dict = self._get_physical_locator_dict(
            dst_ip, None, None, ovsdb_identifier)
        locator = db.get_physical_locator_by_dst_ip(
            context, locator_dict)
        if locator:
            locator_uuid = locator.get('uuid')
        for locator in locator_list:
            if(locator.get('dst_ip') == dst_ip):
                (locator.get('macs')).extend(mac_list)
                return locator_list
        pl_dict = self._get_physical_locator_dict(
            dst_ip, locator_uuid, mac_list)
        locator_list.append(pl_dict)
        return locator_list

    def create_l2_gateway(self, context, l2_gateway):
        pass

    def create_l2_gateway_postcommit(self, context, l2_gateway):
        pass

    def update_l2_gateway(self, context, l2_gateway_id, l2_gateway):
        """Update l2 gateway."""
        pass

    def update_l2_gateway_postcommit(self, context, l2_gateway):
        pass

    def delete_l2_gateway(self, context, id):
        """delete the l2 gateway by id."""
        self.l2gateway_db._admin_check(context, 'DELETE')
        with context.session.begin(subtransactions=True):
            gw_db = self.l2gateway_db._get_l2_gateway(context, id)
            if gw_db is None:
                raise l2gw_exc.L2GatewayNotFound(gateway_id=id)
            if gw_db.network_connections:
                raise l2gw_exc.L2GatewayInUse(gateway_id=id)
            return gw_db

    def delete_l2_gateway_postcommit(self, context, l2_gateway_id):
        pass

    def create_l2_gateway_connection(self, context, l2_gateway_connection):
        """Process the call from the CLI and trigger the RPC,

        to update the connection to the gateway.
        """
        u_mac_dict = {}
        ls_dict = {}
        mac_dict = {}
        self.service_plugin._admin_check(context, 'CREATE')
        gw_connection = l2_gateway_connection.get('l2_gateway_connection')
        # validate connection
        self._validate_connection(context, gw_connection)
        # get l2 gateway devices
        l2gateway_devices = (
            self.service_plugin.get_l2gateway_devices_by_gateway_id(
                context, gw_connection.get('l2_gateway_id')))
        for device in l2gateway_devices:
            locator_list = []
            ovsdb_identifier, logical_switch, port_dict = (
                self._process_port_list(context, device,
                                        gw_connection, "CREATE"))
            ls_dict = self._get_logical_switch_dict(
                context, logical_switch, gw_connection)
            ports = self._get_port_details(context,
                                           gw_connection.get('network_id'))
            for port in ports:
                mac_list = []
                if port['device_owner']:
                    dst_ip, ip_address = self._get_ip_details(context, port)
                    mac_ip_pairs = []
                    if isinstance(port.get("allowed_address_pairs"), list):
                        for address_pair in port['allowed_address_pairs']:
                            mac = address_pair['mac_address']
                            mac_ip_pairs.append((mac,
                                                 address_pair['ip_address']))
                    mac_ip_pairs.append((port.get('mac_address'), ip_address))

                    for mac, ip in mac_ip_pairs:
                        mac_remote = self._get_dict(
                            ovsdb_schema.UcastMacsRemote(
                                uuid=None,
                                mac=mac,
                                logical_switch_id=None,
                                physical_locator_id=None,
                                ip_address=ip))
                        if logical_switch:
                            u_mac_dict['mac'] = mac
                            u_mac_dict['ovsdb_identifier'] = ovsdb_identifier
                            u_mac_dict['logical_switch_uuid'] = (
                                logical_switch.get('uuid'))
                            ucast_mac_remote = (
                                db.get_ucast_mac_remote_by_mac_and_ls(
                                    context, u_mac_dict))
                            if not ucast_mac_remote:
                                mac_list.append(mac_remote)
                        else:
                            mac_list.append(mac_remote)
                    locator_list = self._get_locator_list(
                        context, dst_ip, ovsdb_identifier, mac_list,
                        locator_list)
            for locator in locator_list:
                mac_dict[locator.get('dst_ip')] = locator.pop('macs')
                locator.pop('ovsdb_identifier')
            self.agent_rpc.update_connection_to_gateway(
                context, ovsdb_identifier, ls_dict, locator_list, mac_dict,
                port_dict, 'CREATE')

    def _get_identifer_list(self, context, gw_connection):
        identifier_list = []
        l2gateway_devices = (
            self.service_plugin.get_l2gateway_devices_by_gateway_id(
                context, gw_connection.get('l2_gateway_id')))
        for device in l2gateway_devices:
            physical_switch = db.get_physical_switch_by_name(
                context, device.get('device_name'))
            if not physical_switch:
                msg = _('The PHYSICAL SWITCH data not found in the server')
                raise Exception(msg)
            ovsdb_identifier = physical_switch.get('ovsdb_identifier')
            identifier_list.append(ovsdb_identifier)
        return set(identifier_list)

    def _get_set_of_ovsdb_ids(self, context, gw_connection,
                              gw_connection_ovsdb_set):
        ovsdb_id_set = set()
        network_id = gw_connection.get('network_id')
        l2gateway_connections = self.service_plugin.get_l2_gateway_connections(
            context, filters={'network_id': [network_id]})
        for l2gatewayconnection in l2gateway_connections:
            if l2gatewayconnection['id'] == gw_connection['id']:
                l2gateway_connections.remove(l2gatewayconnection)
            else:
                ovsdb_id_set.union(self._get_identifer_list(
                    context, l2gatewayconnection))
        ovsdb_id_set = gw_connection_ovsdb_set.difference(ovsdb_id_set)
        return ovsdb_id_set

    def _remove_vm_macs(self, context, network_id, ovsdb_id_set):
        ports = self._get_port_details(context, network_id)
        if ports:
            for ovsdb_id in list(ovsdb_id_set):
                for port in ports:
                    port['ovsdb_identifier'] = ovsdb_id
                self.delete_port_mac(context, ports)

    def create_l2_gateway_connection_postcommit(self, context,
                                                l2_gateway_connection):
        pass

    def delete_l2_gateway_connection(self, context, l2_gateway_connection):
        """Process the call from the CLI and trigger the RPC,

        to update the connection from the gateway.
        """
        locator_list = []
        ls_dict = {}
        mac_dict = {}
        self.service_plugin._admin_check(context, 'DELETE')
        gw_connection = self.service_plugin.get_l2_gateway_connection(
            context, l2_gateway_connection)
        if not gw_connection:
            raise l2gw_exc.L2GatewayConnectionNotFound(l2_gateway_connection)
        gw_connection_ovsdb_set = self._get_identifer_list(context,
                                                           gw_connection)
        network_id = gw_connection.get('network_id')
        # get list of ovsdb_ids
        ovsdb_id_set = self._get_set_of_ovsdb_ids(context,
                                                  gw_connection,
                                                  gw_connection_ovsdb_set)
        # call delete connection RPC to gw_connection_ovsdb_set
        l2gateway_devices = (
            self.service_plugin.get_l2gateway_devices_by_gateway_id(
                context, gw_connection.get('l2_gateway_id')))
        for device in l2gateway_devices:
            port_dict = {}
            (ovsdb_identifier, logical_switch, port_dict) = (
                self._process_port_list(
                    context, device, gw_connection,
                    "DELETE", gw_connection_ovsdb_set))
            self.agent_rpc.update_connection_to_gateway(
                context, ovsdb_identifier, ls_dict, locator_list, mac_dict,
                port_dict, 'DELETE')
        # call delete vif_from_gateway for ovsdb_id_set
        self._remove_vm_macs(context, network_id, ovsdb_id_set)

    def delete_l2_gateway_connection_postcommit(self, context,
                                                l2_gateway_connection):
        pass
