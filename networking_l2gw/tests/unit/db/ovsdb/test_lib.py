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

from oslo_db import exception as d_exc
from oslo_utils import timeutils
from oslo_utils import uuidutils

from neutron.tests.unit import testlib_api
from neutron_lib import context

from networking_l2gw.db.l2gateway.ovsdb import lib
from networking_l2gw.db.l2gateway.ovsdb import models

_uuid = uuidutils.generate_uuid


class OvsdbLibTestCase(testlib_api.SqlTestCase):

    def setUp(self):
        super(OvsdbLibTestCase, self).setUp()
        self.ctx = context.get_admin_context()

    def _get_logical_switch_dict(self):
        uuid = _uuid()
        record_dict = {'uuid': uuid,
                       'name': 'logical_switch1',
                       'key': '100',
                       'ovsdb_identifier': "host1"}
        return record_dict

    def _create_logical_switch(self, record_dict, name=None):
        if name:
            record_dict['name'] = name
        with self.ctx.session.begin(subtransactions=True):
            entry = models.LogicalSwitches(
                uuid=record_dict['uuid'],
                name=record_dict['name'],
                key=record_dict['key'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_logical_switch(self):
        record_dict = self._get_logical_switch_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_logical_switch(record_dict)
        result = lib.get_logical_switch(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_get_logical_switch_return_none(self):
        record_dict = {'uuid': 'foo_uuid', 'ovsdb_identifier': 'foo_ovsdb_id'}
        result = lib.get_logical_switch(self.ctx, record_dict)
        self.assertIsNone(result)

    def test_add_logical_switch(self):
        record_dict = self._get_logical_switch_dict()
        self._create_logical_switch(record_dict)
        count = self.ctx.session.query(models.LogicalSwitches).count()
        self.assertEqual(1, count)

    def test_delete_logical_switch(self):
        record_dict = self._get_logical_switch_dict()
        self._create_logical_switch(record_dict)
        lib.delete_logical_switch(self.ctx, record_dict)
        count = self.ctx.session.query(models.LogicalSwitches).count()
        self.assertEqual(count, 0)

    def _get_physical_locator_dict(self):
        uuid = _uuid()
        record_dict = {'uuid': uuid,
                       'dst_ip': '10.0.0.1',
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_physical_locator(self, record_dict, dst_ip=None):
        if dst_ip:
            record_dict['dst_ip'] = dst_ip
        with self.ctx.session.begin(subtransactions=True):
            entry = models.PhysicalLocators(
                uuid=record_dict['uuid'],
                dst_ip=record_dict['dst_ip'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_physical_locator(self):
        record_dict = self._get_physical_locator_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_locator(record_dict)
        result = lib.get_physical_locator(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_physical_locator(self):
        record_dict = self._get_physical_locator_dict()
        self._create_physical_locator(record_dict)
        count = self.ctx.session.query(models.PhysicalLocators).count()
        self.assertEqual(1, count)

    def test_delete_physical_locator(self):
        record_dict = self._get_physical_locator_dict()
        self._create_physical_locator(record_dict)
        lib.delete_physical_locator(self.ctx, record_dict)
        count = self.ctx.session.query(models.PhysicalLocators).count()
        self.assertEqual(count, 0)

    def _get_physical_switch_dict(self):
        uuid = _uuid()
        record_dict = {'uuid': uuid,
                       'name': 'physical_switch1',
                       'tunnel_ip': '10.0.0.1',
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_physical_switch(self, record_dict, name=None):
        if name:
            record_dict['name'] = name
        with self.ctx.session.begin(subtransactions=True):
            entry = models.PhysicalSwitches(
                uuid=record_dict['uuid'],
                name=record_dict['name'],
                tunnel_ip=record_dict['tunnel_ip'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_physical_switch(self):
        record_dict = self._get_physical_switch_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_switch(record_dict)
        result = lib.get_physical_switch(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_physical_switch(self):
        record_dict = self._get_physical_switch_dict()
        self._create_physical_switch(record_dict)
        count = self.ctx.session.query(models.PhysicalSwitches).count()
        self.assertEqual(1, count)

    def test_add_physical_switch_raise_on_duplicate_constraint(self):
        record_dict = self._get_physical_switch_dict()
        self._create_physical_switch(record_dict)
        # Call the method twice to trigger a db duplicate constraint error,
        # this time with a different switch name!
        self.assertRaises(d_exc.DBDuplicateEntry,
                          self._create_physical_switch,
                          record_dict, 'physical_switch2')

    def test_delete_physical_switch(self):
        record_dict = self._get_physical_switch_dict()
        self._create_physical_switch(record_dict)
        lib.delete_physical_switch(self.ctx, record_dict)
        count = self.ctx.session.query(models.PhysicalSwitches).count()
        self.assertEqual(count, 0)

    def _get_physical_port_dict(self):
        uuid = _uuid()
        ps_id = _uuid()
        record_dict = {'uuid': uuid,
                       'name': 'physical_port1',
                       'physical_switch_id': ps_id,
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_physical_port(self,
                              record_dict,
                              name=None,
                              physical_switch_id=None):
        if name and physical_switch_id:
            record_dict['name'] = name
            record_dict['physical_switch_id'] = physical_switch_id
        with self.ctx.session.begin(subtransactions=True):
            entry = models.PhysicalPorts(
                uuid=record_dict['uuid'],
                name=record_dict['name'],
                physical_switch_id=record_dict['physical_switch_id'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_physical_port(self):
        record_dict = self._get_physical_port_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_port(record_dict)
        result = lib.get_physical_port(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_physical_port(self):
        record_dict = self._get_physical_port_dict()
        self._create_physical_port(record_dict)
        count = self.ctx.session.query(models.PhysicalPorts).count()
        self.assertEqual(1, count)

    def test_add_physical_port_raise_on_duplicate_constraint(self):
        record_dict = self._get_physical_port_dict()
        self._create_physical_port(record_dict)
        # Call the method twice to trigger a db duplicate constraint error,
        # this time with a different switch name and physical switch id!
        self.assertRaises(d_exc.DBDuplicateEntry,
                          self._create_physical_port,
                          record_dict, 'physical_port2', _uuid())

    def test_delete_physical_port(self):
        record_dict = self._get_physical_port_dict()
        self._create_physical_port(record_dict)
        lib.delete_physical_port(self.ctx, record_dict)
        count = self.ctx.session.query(models.PhysicalPorts).count()
        self.assertEqual(count, 0)

    def _get_ucast_mac_local_dict(self):
        uuid = _uuid()
        ls_id = _uuid()
        pl_id = _uuid()
        record_dict = {'uuid': uuid,
                       'mac': '12:34:56:78:90:aa:bb',
                       'logical_switch_id': ls_id,
                       'physical_locator_id': pl_id,
                       'ip_address': '10.0.0.1',
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_ucast_mac_local(self, record_dict):
        with self.ctx.session.begin(subtransactions=True):
            entry = models.UcastMacsLocals(
                uuid=record_dict['uuid'],
                mac=record_dict['mac'],
                logical_switch_id=record_dict['logical_switch_id'],
                physical_locator_id=record_dict['physical_locator_id'],
                ip_address=record_dict['ip_address'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_ucast_mac_local(self):
        record_dict = self._get_ucast_mac_local_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_ucast_mac_local(record_dict)
        result = lib.get_ucast_mac_local(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_ucast_mac_local(self):
        record_dict = self._get_ucast_mac_local_dict()
        self._create_ucast_mac_local(record_dict)
        count = self.ctx.session.query(models.UcastMacsLocals).count()
        self.assertEqual(1, count)

    def test_add_ucast_mac_local_raise_on_duplicate_constraint(self):
        record_dict = self._get_ucast_mac_local_dict()
        self._create_ucast_mac_local(record_dict)
        # Call the method twice to trigger a db duplicate constraint error,
        # this time with a different mac and logical switch id!
        record_dict['mac'] = '11:22:33:44:55:66:77'
        record_dict['logical_switch_id'] = _uuid()
        self.assertRaises(d_exc.DBDuplicateEntry,
                          self._create_ucast_mac_local,
                          record_dict)

    def test_delete_ucast_mac_local(self):
        record_dict = self._get_ucast_mac_local_dict()
        self._create_ucast_mac_local(record_dict)
        lib.delete_ucast_mac_local(self.ctx, record_dict)
        count = self.ctx.session.query(models.UcastMacsLocals).count()
        self.assertEqual(count, 0)

    def _get_ucast_mac_remote_dict(self):
        uuid = _uuid()
        ls_id = _uuid()
        pl_id = _uuid()
        record_dict = {'uuid': uuid,
                       'mac': '12:34:56:78:90:aa:bb',
                       'logical_switch_id': ls_id,
                       'physical_locator_id': pl_id,
                       'ip_address': '10.0.0.1',
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_ucast_mac_remote(self,
                                 record_dict,
                                 mac=None,
                                 logical_switch_uuid=None):
        if mac and logical_switch_uuid:
            record_dict['mac'] = mac
            record_dict['logical_switch_id'] = logical_switch_uuid
        with self.ctx.session.begin(subtransactions=True):
            entry = models.UcastMacsRemotes(
                uuid=record_dict['uuid'],
                mac=record_dict['mac'],
                logical_switch_id=record_dict['logical_switch_id'],
                physical_locator_id=record_dict['physical_locator_id'],
                ip_address=record_dict['ip_address'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_ucast_mac_remote(self):
        record_dict = self._get_ucast_mac_remote_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_ucast_mac_remote(record_dict)
        result = lib.get_ucast_mac_remote(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_ucast_mac_remote(self):
        record_dict = self._get_ucast_mac_remote_dict()
        self._create_ucast_mac_remote(record_dict)
        count = self.ctx.session.query(models.UcastMacsRemotes).count()
        self.assertEqual(1, count)

    def test_add_ucast_mac_remote_raise_on_duplicate_constraint(self):
        record_dict = self._get_ucast_mac_remote_dict()
        self._create_ucast_mac_remote(record_dict)
        # Call the method twice to trigger a db duplicate constraint error,
        # this time with a different mac and logical switch id!
        self.assertRaises(d_exc.DBDuplicateEntry,
                          self._create_ucast_mac_remote,
                          record_dict, '11:22:33:44:55:66:77', _uuid())

    def test_delete_ucast_mac_remote(self):
        record_dict = self._get_ucast_mac_remote_dict()
        self._create_ucast_mac_remote(record_dict)
        lib.delete_ucast_mac_remote(self.ctx, record_dict)
        count = self.ctx.session.query(models.UcastMacsRemotes).count()
        self.assertEqual(count, 0)

    def _get_vlan_binding_dict(self):
        port_uuid = _uuid()
        ls_uuid = _uuid()
        record_dict = {'port_uuid': port_uuid,
                       'vlan': 200,
                       'logical_switch_uuid': ls_uuid,
                       'ovsdb_identifier': 'host1'}
        return record_dict

    def _create_vlan_binding(self, record_dict, port_uuid=None):
        if port_uuid:
            record_dict['port_uuid'] = port_uuid
        with self.ctx.session.begin(subtransactions=True):
            entry = models.VlanBindings(
                port_uuid=record_dict['port_uuid'],
                vlan=record_dict['vlan'],
                logical_switch_uuid=record_dict['logical_switch_uuid'],
                ovsdb_identifier=record_dict['ovsdb_identifier'])
            self.ctx.session.add(entry)
            return entry

    def test_get_vlan_binding(self):
        record_dict = self._get_vlan_binding_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_vlan_binding(record_dict)
        result = lib.get_vlan_binding(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_add_vlan_binding(self):
        record_dict = self._get_vlan_binding_dict()
        self._create_vlan_binding(record_dict)
        count = self.ctx.session.query(models.VlanBindings).count()
        self.assertEqual(1, count)

    def test_add_vlan_binding_raise_on_duplicate_constraint(self):
        record_dict = self._get_vlan_binding_dict()
        self._create_vlan_binding(record_dict)
        # Call the method twice to trigger a db duplicate constraint error,
        # this time with a same entries
        self.assertRaises(d_exc.DBDuplicateEntry,
                          self._create_vlan_binding,
                          record_dict)

    def test_delete_vlan_binding(self):
        record_dict = self._get_vlan_binding_dict()
        self._create_vlan_binding(record_dict)
        lib.delete_vlan_binding(self.ctx, record_dict)
        count = self.ctx.session.query(models.VlanBindings).count()
        self.assertEqual(count, 0)

    def test_get_logical_switch_by_name(self):
        record_dict = self._get_logical_switch_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_logical_switch(record_dict,
                                                'logical_switch2')
        record_dict['logical_switch_name'] = 'logical_switch2'
        result = lib.get_logical_switch_by_name(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_get_all_logical_switch_by_name(self):
        record_dict1 = self._get_logical_switch_dict()
        self._create_logical_switch(record_dict1, 'logical_switch2')
        record_dict2 = self._get_logical_switch_dict()
        self._create_logical_switch(record_dict2, 'logical_switch2')
        ls_list = lib.get_all_logical_switches_by_name(self.ctx,
                                                       'logical_switch2')
        self.assertEqual(2, len(ls_list))

    def test_get_physical_locator_by_dst_ip(self):
        record_dict = self._get_physical_locator_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_locator(record_dict, '20.0.0.1')
        record_dict['dst_ip'] = '20.0.0.1'
        record_dict.pop('uuid')
        result = lib.get_physical_locator_by_dst_ip(self.ctx, record_dict)
        self.assertEqual(entry, result)

    def test_get_physical_switch_by_name(self):
        record_dict = self._get_physical_switch_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_switch(record_dict,
                                                 'physical_switch2')
        result = lib.get_physical_switch_by_name(self.ctx,
                                                 'physical_switch2')
        self.assertEqual(entry, result)

    def test_get_all_vlan_bindings_by_physical_port(self):
        record_dict1 = {'port_uuid': 'ps123',
                        'vlan': 200,
                        'logical_switch_uuid': 'ls123',
                        'ovsdb_identifier': 'host1'}
        self._create_vlan_binding(record_dict1)
        record_dict1['vlan'] = 300
        record_dict1['logical_switch_uuid'] = 'ls456'
        self._create_vlan_binding(record_dict1)
        record_dict1['uuid'] = record_dict1.get('port_uuid')
        vlan_list = lib.get_all_vlan_bindings_by_physical_port(self.ctx,
                                                               record_dict1)
        self.assertEqual(2, len(vlan_list))

    def test_get_ucast_mac_remote_by_mac_and_ls(self):
        record_dict = self._get_ucast_mac_remote_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_ucast_mac_remote(record_dict,
                                                  '00:11:22:33:44:55:66',
                                                  'ls123')
        record_dict['mac'] = '00:11:22:33:44:55:66'
        record_dict['logical_switch_uuid'] = 'ls123'
        result = lib.get_ucast_mac_remote_by_mac_and_ls(self.ctx,
                                                        record_dict)
        self.assertEqual(entry, result)

    def test_get_ucast_mac_remote_by_mac_and_ls_when_not_found(self):
        record_dict = self._get_ucast_mac_remote_dict()
        record_dict['mac'] = '00:11:22:33:44:55:66'
        record_dict['logical_switch_uuid'] = 'ls123'
        result = lib.get_ucast_mac_remote_by_mac_and_ls(self.ctx,
                                                        record_dict)
        self.assertEqual(result, None)

    def test_get_physical_port_by_name_and_ps(self):
        record_dict = self._get_physical_port_dict()
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_physical_port(record_dict,
                                               'port1',
                                               'ps123')
        record_dict['interface_name'] = 'port1'
        record_dict['physical_switch_id'] = 'ps123'
        result = lib.get_physical_port_by_name_and_ps(self.ctx,
                                                      record_dict)
        self.assertEqual(entry, result)

    def _get_pending_mac_dict(self, timestamp):
        record_dict = {'uuid': _uuid(),
                       'mac': 'aa:aa:aa:aa:aa:aa',
                       'logical_switch_uuid': 'fake_ls_id',
                       'locator_uuid': _uuid(),
                       'dst_ip': '1.1.1.1',
                       'vm_ip': '2.2.2.2',
                       'ovsdb_identifier': 'ovsdb1',
                       'operation': 'insert',
                       'timestamp': timestamp}
        return record_dict

    def _create_pending_mac(self, record_dict):
        with self.ctx.session.begin(subtransactions=True):
            entry = models.PendingUcastMacsRemote(
                uuid=record_dict['uuid'],
                mac=record_dict['mac'],
                logical_switch_uuid=record_dict['logical_switch_uuid'],
                locator_uuid=record_dict['locator_uuid'],
                dst_ip=record_dict['dst_ip'],
                vm_ip=record_dict['vm_ip'],
                ovsdb_identifier=record_dict['ovsdb_identifier'],
                operation=record_dict['operation'],
                timestamp=record_dict['timestamp'])
            self.ctx.session.add(entry)
            return entry

    def test_add_pending_ucast_mac_remote(self):
        timestamp = timeutils.utcnow()
        record_dict = self._get_pending_mac_dict(timestamp)
        self._create_pending_mac(record_dict)
        count = self.ctx.session.query(models.PendingUcastMacsRemote).count()
        self.assertEqual(1, count)

    def test_get_pending_ucast_mac_remote(self):
        timestamp = timeutils.utcnow()
        record_dict = self._get_pending_mac_dict(timestamp)
        with self.ctx.session.begin(subtransactions=True):
            entry = self._create_pending_mac(record_dict)
        result = lib.get_pending_ucast_mac_remote(
            self.ctx, record_dict['ovsdb_identifier'],
            record_dict['mac'], record_dict['logical_switch_uuid'])
        self.assertEqual(entry, result)

    def test_get_all_pending_remote_macs_in_asc_order(self):
        timestamp1 = timeutils.utcnow()
        record_dict1 = self._get_pending_mac_dict(timestamp1)
        timestamp2 = timeutils.utcnow()
        record_dict2 = self._get_pending_mac_dict(timestamp2)
        with self.ctx.session.begin(subtransactions=True):
            entry1 = self._create_pending_mac(record_dict1)
            entry2 = self._create_pending_mac(record_dict2)
        result = lib.get_all_pending_remote_macs_in_asc_order(
            self.ctx, record_dict1['ovsdb_identifier'])
        self.assertEqual(result[0], entry1)
        self.assertEqual(result[1], entry2)

    def test_delete_pending_ucast_mac_remote(self):
        timestamp = timeutils.utcnow()
        record_dict = self._get_pending_mac_dict(timestamp)
        self._create_pending_mac(record_dict)
        lib.delete_pending_ucast_mac_remote(self.ctx,
                                            record_dict['operation'],
                                            record_dict['ovsdb_identifier'],
                                            record_dict['logical_switch_uuid'],
                                            record_dict['mac'])
        count = self.ctx.session.query(models.UcastMacsRemotes).count()
        self.assertEqual(count, 0)

    def test_get_all_ucast_mac_remote_by_ls(self):
        record_dict = self._get_ucast_mac_remote_dict()
        record_dict1 = self._create_ucast_mac_remote(record_dict)
        record_dict = self._get_ucast_mac_remote_dict()
        record_dict['mac'] = '00:11:22:33:44:55:66'
        record_dict['logical_switch_id'] = record_dict1.get(
            'logical_switch_id')
        self._create_ucast_mac_remote(record_dict)
        mac_list = lib.get_all_ucast_mac_remote_by_ls(self.ctx, record_dict)
        self.assertEqual(2, len(mac_list))
