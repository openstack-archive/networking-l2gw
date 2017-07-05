# Copyright 2015 OpenStack Foundation
# Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import json
import time

from neutron.tests.api import base
from neutron.tests.tempest import exceptions
from neutron.tests.tempest import manager
from oslo_log import log
from tempest.lib.common import rest_client
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc

from networking_l2gw.tests.api import base_l2gw
from networking_l2gw.tests.scenario import ovsdb_connections
from networking_l2gw.tests.tempest import config

CONF = config.CONF
LOG = log.getLogger(__name__)
OVSDB_IP = CONF.network.ovsdb_ip
OVSDB_PORT = CONF.network.ovsdb_port
OVSDB_SCHEMA_NAME = CONF.network.ovsdb_schema_name


class TestL2GatewayBasic(base.BaseAdminNetworkTest):

    """This test case tests the basic end to end functionality of l2-gateway

       and tests whether the appropriate entries are getting registered in

       the ovsdb.
    """

    @classmethod
    def resource_setup(cls):
        super(TestL2GatewayBasic, cls).resource_setup()
        nova_creds = cls.isolated_creds.get_admin_creds()
        cls.auth_provider = manager.get_auth_provider(nova_creds)

    def _create_server(
            self, name=None,
            network=None, wait_on_boot=True, wait_on_delete=True):
        region = CONF.compute.region
        image = CONF.compute.image_ref
        flavor = CONF.compute.flavor_ref
        rs_client = rest_client.RestClient(
            self.auth_provider, 'compute', region)
        data = {'server': {
            'name': name,
            'imageRef': image,
            'flavorRef': flavor,
            'max_count': 1,
            'min_count': 1,
            'networks': [{'uuid': network}]}}
        data = json.dumps(data)
        (resp, body,) = rs_client.post('/servers', data)
        rs_client.expected_success(202, resp.status)
        body = json.loads(body)
        server_id = body['server']['id']
        self.wait_for_server_status(server_id, 'ACTIVE')
        return server_id

    def _delete_server(self, server=None):
        rs_client = rest_client.RestClient(
            self.auth_provider, 'compute', 'RegionOne')
        (resp, body, ) = rs_client.delete('servers/%s' % str(server))
        self.wait_for_server_termination(server)
        rest_client.ResponseBody(resp, body)

    def wait_for_server_status(self, server_id, status, ready_wait=True,
                               extra_timeout=0, raise_on_error=True):
        """Waits for a server to reach a given status."""
        build_timeout = CONF.compute.build_timeout
        build_interval = CONF.boto.build_interval

        def _get_task_state(body):
            return body.get('OS-EXT-STS:task_state', None)
        rs = rest_client.RestClient(self.auth_provider, "compute", "RegionOne")
        resp, body = rs.get("servers/%s" % str(server_id))
        body = json.loads(body)
        old_status = server_status = body['server']['status']
        old_task_state = task_state = _get_task_state(body)
        start_time = int(time.time())
        timeout = build_timeout + extra_timeout
        while True:
            if status == 'BUILD' and server_status != 'UNKNOWN':
                return
            if server_status == status:
                if ready_wait:
                    if status == 'BUILD':
                        return
                    if str(task_state) == "None":
                        time.sleep(CONF.compute.ready_wait)
                        return
                else:
                    return
            time.sleep(build_interval)
            resp, body = rs.get("servers/%s" % str(server_id))
            body = json.loads(body)
            server_status = body['server']['status']
            task_state = _get_task_state(body)
            if (server_status != old_status) or (task_state != old_task_state):
                oldstatus = '/'.join((old_status, str(old_task_state)))
                serverstatus = '/'.join((server_status, str(task_state)))
                waitsec = (time.time() - start_time)
                LOG.info(
                    'State transition %(oldstatus)s => %(serverstatus)s'
                    'after %(waitsec)d second wait' %
                    {'oldstatus': oldstatus, 'serverstatus': serverstatus,
                     'waitsec': waitsec}
                )
            if (server_status == 'ERROR') and raise_on_error:
                if 'fault' in body:
                    raise exceptions.BuildErrorException(body['fault'],
                                                         server_id=server_id)
                else:
                    raise exceptions.BuildErrorException(server_id=server_id)
            timed_out = int(time.time()) - start_time >= timeout
            if timed_out:
                expected_task_state = 'None' if ready_wait else 'n/a'
                message = ('Server %(server_id)s failed to reach %(status)s '
                           'status and task state "%(expected_task_state)s" '
                           'within the required time (%(timeout)s s).' %
                           {'server_id': server_id,
                            'status': status,
                            'expected_task_state': expected_task_state,
                            'timeout': timeout})
                message += ' Current status: %s.' % server_status
                message += ' Current task state: %s.' % task_state
                caller = test_utils.find_test_caller()
                if caller:
                    message = '(%s) %s' % (caller, message)
                raise exceptions.TimeoutException(message)
            old_status = server_status
            old_task_state = task_state

    def wait_for_server_termination(self, server_id, ignore_error=False):
        """Waits for server to reach termination."""
        build_interval = CONF.boto.build_interval
        while True:
            try:
                rs = rest_client.RestClient(
                    self.auth_provider, 'compute', 'RegionOne')
                (resp, body,) = rs.get('servers/%s' % str(server_id))
                body = json.loads(body)
            except lib_exc.NotFound:
                return
            server_status = body['server']['status']
            if server_status == 'ERROR' and not ignore_error:
                raise exceptions.BuildErrorException(server_id=server_id)
            time.sleep(build_interval)

    def validate_ovsdb(self, seg_id, port, network_id_1, tunnel_key):
        # Check Logical_Switch
        objConnection = ovsdb_connections.OVSDBConnection(OVSDB_IP, OVSDB_PORT)
        resp = objConnection.get_response(
            OVSDB_IP, OVSDB_PORT, "Logical_Switch")
        resp_dec = json.loads(resp)
        count = resp.count('_uuid')
        try:
            self.assertIn(str(network_id_1), resp)
        except Exception:
            raise lib_exc.NotFound("Network not found in Logical Switch table")
        row = objConnection.find_row(network_id_1, count, resp_dec)
        try:
            self.assertIn(str(tunnel_key), row)
        except Exception:
            raise lib_exc.NotFound(
                "Tunnel key not found in Logical Switch table")
        objConnection.stop("true")

        # Check Physical_Port
        objConnection = ovsdb_connections.OVSDBConnection(OVSDB_IP, OVSDB_PORT)
        resp = objConnection.get_response(
            OVSDB_IP, OVSDB_PORT, "Physical_Port")
        count = resp.count('_uuid')
        try:
            self.assertIn(str(seg_id[0]), resp)
        except Exception:
            raise lib_exc.NotFound(
                "Segmentation ID not found in Physical Port table")
        objConnection.stop("true")

        # Check Physical_Locator
        objConnection = ovsdb_connections.OVSDBConnection(OVSDB_IP, OVSDB_PORT)
        resp = objConnection.get_response(
            OVSDB_IP, OVSDB_PORT, "Physical_Locator")
        count = resp.count('_uuid')
        port_str = str(port)
        count_port = port_str.count('fixed_ips')
        net_node_host = []
        compute_node_host = []
        # Extracting unique Network node host name and Compute host name
        for i in range(count_port):
            net_id = port['ports'][i]['network_id']
            device_owner = port['ports'][i]['device_owner']
            if net_id == network_id_1 and device_owner == 'network:dhcp':
                if port['ports'][i]['binding:host_id'] not in net_node_host:
                    net_node_host.append(port['ports'][i]['binding:host_id'])
            if port['ports'][i]['device_owner'] == 'compute:None':
                if port['ports'][i]['binding:host_id'] not in net_node_host:
                    compute_node_host.append(
                        port['ports'][i]['binding:host_id'])
        ip_SW = CONF.network.l2gw_switch_ip
        host_and_ip = CONF.network.hosts
        list_ = host_and_ip.split(', ')
        host_ip_dict = {}
        for i in list_:
            sub_list = i.split(':')
            host = sub_list[0]
            ip = sub_list[1]
            host_ip_dict.update({host: ip})
        for net_node in net_node_host:
            ip_NN = host_ip_dict[net_node]
            try:
                self.assertIn(ip_NN, resp)
            except Exception:
                raise lib_exc.NotFound(
                    "Network Node IP not found in Physical Locator table")
        for compute_node in compute_node_host:
            ip_CN = host_ip_dict[compute_node]
            try:
                self.assertIn(ip_CN, resp)
            except Exception:
                raise lib_exc.NotFound(
                    "Compute Node IP not found in Physical Locator table")
        try:
            self.assertIn(ip_SW, resp)
        except Exception:
            raise lib_exc.NotFound(
                "Switch IP not found in Physical Locator table")
        objConnection.stop("true")

        # Check Ucast_macs_Remote
        objConnection = ovsdb_connections.OVSDBConnection(OVSDB_IP, OVSDB_PORT)
        resp = objConnection.get_response(
            OVSDB_IP, OVSDB_PORT, "Ucast_Macs_Remote")
        ip_mac_dict = {}
        count_uuid = resp.count('_uuid')
        resp_dec = json.loads(resp)
        for i in range(count_port):
            mac = port['ports'][i]['mac_address']
            ip = port['ports'][i]['fixed_ips'][0]['ip_address']
            ip_mac_dict.update({mac: ip})
        try:
            for key, value in ip_mac_dict.items():
                row = objConnection.find_row(key, count_uuid, resp_dec)
                self.assertIn(value, row)
        except Exception:
            raise lib_exc.NotFound(
                "MAC & its port not found in UCast MAC Remote table")
        objConnection.stop("true")

    def _create_l2_gateway(self, name, devices):
        body_l2gateway = self.admin_client.create_l2_gateway(
            name=name, devices=devices)
        self.addCleanup(
            self.admin_client.delete_l2_gateway,
            body_l2gateway['l2_gateway']['id'])
        return body_l2gateway

    def _create_l2_gw_connection(
            self, l2gw, net_id, seg_id=None, explicit=None):
        l2gw_id = l2gw['l2_gateway']['id']
        if l2gw['l2_gateway']['devices'][0]['interfaces'][
           0]['segmentation_id']:
            resp_l2gwconn = self.admin_client.create_l2_gateway_connection(
                network_id=net_id, l2_gateway_id=l2gw_id)
        else:
            resp_l2gwconn = self.admin_client.create_l2_gateway_connection(
                network_id=net_id,
                l2_gateway_id=l2gw_id, segmentation_id=seg_id)
        if explicit:
            # Connection deleted explicitly, thus addCleanup not called
            pass
        else:
            self.addCleanup(
                self.admin_client.delete_l2_gateway_connection,
                resp_l2gwconn['l2_gateway_connection']['id'])
        return resp_l2gwconn

    def _setup_network_and_server(self, cidr=None):
        network = self.create_network()
        self.addCleanup(self.client.delete_network, network['id'])
        self.create_subnet(network=network, cidr=cidr)
        name = data_utils.rand_name('server-smoke')
        server_id = self._create_server(name, network=network['id'])
        self.addCleanup(self._delete_server, server_id)
        return network

    def test_l2gw_create_connection(self):
        network = self._setup_network_and_server()
        network_body = self.admin_client.show_network(network['id'])
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)['devices']
        l2_gw_body = self._create_l2_gateway(name=gw_name, devices=devices)
        segmentation_id = l2_gw_body['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        self._create_l2_gw_connection(l2_gw_body, network['id'])
        tunnel_key = network_body['network']['provider:segmentation_id']
        port = self.admin_client.list_ports()
        self.validate_ovsdb(segmentation_id, port, network['id'], tunnel_key)

    def test_multiple_connections(self):
        # Create first connection and validate
        network = self._setup_network_and_server()
        network_body = self.admin_client.show_network(network['id'])
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)['devices']
        l2_gw_body = self._create_l2_gateway(name=gw_name, devices=devices)
        segmentation_id = l2_gw_body['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        self._create_l2_gw_connection(l2_gw_body, network['id'])
        tunnel_key = network_body['network']['provider:segmentation_id']
        port = self.admin_client.list_ports()
        self.validate_ovsdb(segmentation_id, port, network['id'], tunnel_key)
        # Create second connection and validate
        network_2 = self._setup_network_and_server()
        network_body_2 = self.admin_client.show_network(network_2['id'])
        gw_name_2 = data_utils.rand_name('l2gw')
        devices_2 = base_l2gw.get_l2gw_body(
            CONF.network.l2gw_switch_2)['devices']
        l2_gw_body_2 = self._create_l2_gateway(
            name=gw_name_2, devices=devices_2)
        segmentation_id_2 = l2_gw_body_2['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        self._create_l2_gw_connection(l2_gw_body_2, network_2['id'])
        tunnel_key_2 = network_body_2['network']['provider:segmentation_id']
        port_2 = self.admin_client.list_ports()
        self.validate_ovsdb(
            segmentation_id_2, port_2, network_2['id'], tunnel_key_2)

    def test_boot_vm_after_create_connection(self):
        network = self.create_network()
        self.addCleanup(self.client.delete_network, network['id'])
        self.create_subnet(network)
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)['devices']
        l2_gw_body = self._create_l2_gateway(name=gw_name, devices=devices)
        segmentation_id = l2_gw_body['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        self._create_l2_gw_connection(l2_gw_body, network['id'])
        name = data_utils.rand_name('server-smoke')
        server_id = self._create_server(name, network=network['id'])
        self.addCleanup(self._delete_server, server_id)
        network_body = self.admin_client.show_network(network['id'])
        segmentation_id = l2_gw_body['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        tunnel_key = network_body['network']['provider:segmentation_id']
        port = self.admin_client.list_ports()
        self.validate_ovsdb(segmentation_id, port, network['id'], tunnel_key)

    def test_create_new_connection_after_deleting_old_one(self):
        network = self._setup_network_and_server()
        network_body = self.admin_client.show_network(network['id'])
        gw_name = data_utils.rand_name('l2gw')
        devices = base_l2gw.get_l2gw_body(CONF.network.l2gw_switch)['devices']
        l2_gw_body = self._create_l2_gateway(name=gw_name, devices=devices)
        segmentation_id = l2_gw_body['l2_gateway']['devices'][0][
            'interfaces'][0]['segmentation_id']
        # Create a connection and validate ovsdb
        l2gw_connection = self._create_l2_gw_connection(
            l2_gw_body, network['id'], explicit=True)
        tunnel_key = network_body['network']['provider:segmentation_id']
        port = self.admin_client.list_ports()
        self.validate_ovsdb(segmentation_id, port, network['id'], tunnel_key)
        # Delete and create new connection and validate ovsdb
        self.admin_client.delete_l2_gateway_connection(
            l2gw_connection['l2_gateway_connection']['id'])
        self._create_l2_gw_connection(l2_gw_body, network['id'])
        self.validate_ovsdb(segmentation_id, port, network['id'], tunnel_key)
