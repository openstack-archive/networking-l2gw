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


class PhysicalLocator(object):
    def __init__(self, uuid, dst_ip):
        self.uuid = uuid
        self.dst_ip = dst_ip


class PhysicalSwitch(object):
    def __init__(self, uuid, name, tunnel_ip, switch_fault_status):
        self.uuid = uuid
        self.name = name
        self.tunnel_ip = tunnel_ip
        self.switch_fault_status = switch_fault_status


class PhysicalPort(object):
    def __init__(self, uuid, name, phys_switch_id, vlan_binding_dicts,
                 port_fault_status):
        self.uuid = uuid
        self.name = name
        self.physical_switch_id = phys_switch_id
        self.vlan_bindings = []
        self.port_fault_status = port_fault_status
        if vlan_binding_dicts:
            for vlan_binding in vlan_binding_dicts:
                v_binding = VlanBinding(vlan_binding['vlan'],
                                        vlan_binding['logical_switch_uuid'])
                self.vlan_bindings.append(v_binding)


class LogicalSwitch(object):
    def __init__(self, uuid, name, key, description):
        self.uuid = uuid
        self.name = name
        self.key = key
        self.description = description


class UcastMacsLocal(object):
    def __init__(self, uuid, mac, logical_switch_id, physical_locator_id,
                 ip_address):
        self.uuid = uuid
        self.mac = mac
        self.logical_switch_id = logical_switch_id
        self.physical_locator_id = physical_locator_id
        self.ip_address = ip_address


class UcastMacsRemote(object):
    def __init__(self, uuid, mac, logical_switch_id, physical_locator_id,
                 ip_address):
        self.uuid = uuid
        self.mac = mac
        self.logical_switch_id = logical_switch_id
        self.physical_locator_id = physical_locator_id
        self.ip_address = ip_address


class VlanBinding(object):
    def __init__(self, vlan, logical_switch_uuid):
        self.vlan = vlan
        self.logical_switch_uuid = logical_switch_uuid


class McastMacsLocal(object):
    def __init__(self, uuid, mac, logical_switch, locator_set,
                 ip_address):
        self.uuid = uuid
        self.mac = mac
        self.logical_switch_id = logical_switch
        self.locator_set = locator_set
        self.ip_address = ip_address


class PhysicalLocatorSet(object):
    def __init__(self, uuid, locators):
        self.uuid = uuid
        self.locators = locators
