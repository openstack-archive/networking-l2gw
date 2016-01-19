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

from neutron.agent.ovsdb.native import commands as cmd
from neutron.agent.ovsdb.native import idlutils
from uuid import UUID

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ListPhysicalSwitchCommand(cmd.BaseCommand):
    def __init__(self, api):
        super(ListPhysicalSwitchCommand, self).__init__(api)

    def run_idl(self, txn):
        self.result = [x.name for x in
                       self.api._tables['Physical_Switch'].rows.values()]


class AddLogicalSwitch(cmd.BaseCommand):
    def __init__(self, api, name, description, tunnel_key, may_exist):
        super(AddLogicalSwitch, self).__init__(api)
        self.name = name
        self.description = description
        self.tunnel_key = tunnel_key
        self.may_exist = may_exist

    def run_idl(self, txn):
        if self.may_exist:
            switch = idlutils.row_by_value(self.api.idl, 'Logical_Switch',
                                           'name',
                                           self.name, None)
            if switch:
                return
        row = txn.insert(self.api._tables['Logical_Switch'])
        row.name = self.name
        row.description = self.description
        row.tunnel_key = self.tunnel_key


class DelLogicalSwitchByNameCommand(cmd.BaseCommand):
    def __init__(self, api, name):
        super(DelLogicalSwitchByNameCommand, self).__init__(api)
        self.name = name

    def run_idl(self, txn):
        switch = idlutils.row_by_value(self.api.idl, 'Logical_Switch',
                                       'name',
                                       self.name, None)
        if switch:
            switch.delete()


class GetPhysicalLocatorList(cmd.BaseCommand):
    def __init__(self, api):
        super(GetPhysicalLocatorList, self).__init__(api)

    def run_idl(self):
        self.result = [[x.uuid, x.dst_ip, x.encapsulation_type]
                       for x in
                       self.api._tables['Physical_Locator'].rows.values()]


class AddUcastMacsRemote(cmd.BaseCommand):
    def __init__(self, api, logical_sw_uuid, locator, mac, ipaddr):
        super(AddUcastMacsRemote, self).__init__(api)
        self.api = api
        self.logical_sw_uuid = logical_sw_uuid
        self.locator = locator
        self.mac = mac
        self.ipaddr = ipaddr

    def run_idl(self, txn):
        switch = self.api._tables['Logical_Switch'].rows.get(
            UUID(self.logical_sw_uuid))
        if not switch:
            raise Exception('Logical Switch not found')

        if not self.locator.uuid:
            locator = txn.insert(self.api._tables['Physical_Locator'])
            locator.dst_ip = self.locator.dst_ip
            locator.encapsulation_type = self.locator.encapsulation_type
            if self.locator.tunnel_key:
                locator.tunnel_key = self.locator.tunnel_key
        else:
            locator = self.api._tables['Physical_Locator'].rows.get(
                UUID(self.locator.uuid))

        row = txn.insert(self.api._tables['Ucast_Macs_Remote'])
        row.MAC = self.mac
        row.ipaddr = self.ipaddr
        row.logical_switch = switch
        row.locator = locator


class DelUcastMacsRemoteByLogicalSwAndMac(cmd.BaseCommand):
    def __init__(self, api, logical_sw_uuid, mac):
        super(DelUcastMacsRemoteByLogicalSwAndMac, self).__init__(api)
        self.logical_sw_uuid = logical_sw_uuid
        self.mac = mac

    def run_idl(self, txn):
        macs = [
            x for x in self.api._tables['Ucast_Macs_Remote'].rows.values()
            if (x.MAC == self.mac and
                x.logical_switch.uuid == UUID(self.logical_sw_uuid))
        ]

        if macs:
            macs[0].delete()


class DelUcastMacsRemote(cmd.BaseCommand):
    def __init__(self, api, uuid):
        super(DelUcastMacsRemote, self).__init__(api)
        self.uuid = uuid

    def run_idl(self, txn):
        row = self.api._tables['Ucast_Macs_Remote'].rows.get(UUID(self.uuid))
        if row:
            row.delete()


class AddMcastMacsRemote(cmd.BaseCommand):
    def __init__(self, api, mac, logical_sw_uuid, locator_list):
        super(AddMcastMacsRemote, self).__init__(api)
        self.mac = mac
        self.logical_sw_uuid = logical_sw_uuid
        self.locator_list = locator_list

    def run_idl(self, txn):
        switch = self.api._tables['Logical_Switch'].rows.get(
            UUID(self.logical_sw_uuid))
        if not switch:
            raise Exception('Logical Switch not found')

        mcast_macs_remote = txn.insert(self.api._tables['Mcast_Macs_Remote'])
        mcast_macs_remote.MAC = self.mac
        mcast_macs_remote.logical_switch = switch

        locator_set = txn.insert(self.api._tables['Physical_Locator_Set'])
        mcast_macs_remote.locator_set = locator_set

        locators = []

        for locator in self.locator_list:
            if not locator.uuid:
                locator_db = txn.insert(self.api._tables['Physical_Locator'])
                locator_db.dst_ip = locator.dst_ip
                locator_db.encapsulation_type = locator.encapsulation_type
                if locator.tunnel_key:
                    locator_db.tunnel_key = locator.tunnel_key
                locators.append(locator_db)
            else:
                locator_db = self.api._tables['Physical_Locator'].rows.get(
                    UUID(locator.uuid))
                locators.append(locator_db)

        locator_set.locators = locators


class DelRemoteConnection(cmd.BaseCommand):
    def __init__(self, api, ipaddr, tunnel_key):
        super(DelRemoteConnection, self).__init__(api)
        self.ipaddr = ipaddr
        self.tunnel_key = tunnel_key

    def run_idl(self, txn):

        locator = next(l for l in self.api._tables[
            'Physical_Locator'].rows.values() if
            (self.tunnel_key in l.tunnel_key) and
            l.dst_ip == self.ipaddr)
        if not locator:
            raise Exception('error finding locator')

        locator_sets = [s for s in self.api._tables[
            'Physical_Locator_Set'].rows.values() if locator in s.locators]

        for m in self.api._tables['Mcast_Macs_Remote'].rows.values():
            for l in locator_sets:
                if m.locator_set == l:
                    r = l.locators
                    r.remove(locator)
                    if r:
                        locator_set = txn.insert(
                            self.api._tables['Physical_Locator_Set'])
                        locator_set.locators = r
                        m.locator_set = locator_set
                    else:
                        m.delete()

        for mac in self.api._tables['Ucast_Macs_Remote'].rows.values():
            if mac.locator == locator:
                mac.delete()
