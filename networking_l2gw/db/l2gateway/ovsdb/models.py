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

from neutron_lib.db import model_base
import sqlalchemy as sa


class PhysicalLocators(model_base.BASEV2):
    __tablename__ = 'physical_locators'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    dst_ip = sa.Column(sa.String(64), nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)


class PhysicalSwitches(model_base.BASEV2):
    __tablename__ = 'physical_switches'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    name = sa.Column(sa.String(255), nullable=True)
    tunnel_ip = sa.Column(sa.String(64), nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)
    switch_fault_status = sa.Column(sa.String(length=32), nullable=True)


class PhysicalPorts(model_base.BASEV2):
    __tablename__ = 'physical_ports'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    name = sa.Column(sa.String(255), nullable=True)
    physical_switch_id = sa.Column(sa.String(36), nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)
    port_fault_status = sa.Column(sa.String(length=32), nullable=True)


class LogicalSwitches(model_base.BASEV2):
    __tablename__ = 'logical_switches'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    name = sa.Column(sa.String(255), nullable=True)
    key = sa.Column(sa.Integer, nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)


class UcastMacsLocals(model_base.BASEV2):
    __tablename__ = 'ucast_macs_locals'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    mac = sa.Column(sa.String(32), nullable=True)
    logical_switch_id = sa.Column(sa.String(36), nullable=True)
    physical_locator_id = sa.Column(sa.String(36), nullable=True)
    ip_address = sa.Column(sa.String(64), nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)


class UcastMacsRemotes(model_base.BASEV2):
    __tablename__ = 'ucast_macs_remotes'
    uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    mac = sa.Column(sa.String(32), nullable=True)
    logical_switch_id = sa.Column(sa.String(36), nullable=True)
    physical_locator_id = sa.Column(sa.String(36), nullable=True)
    ip_address = sa.Column(sa.String(64), nullable=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)


class VlanBindings(model_base.BASEV2):
    __tablename__ = 'vlan_bindings'
    port_uuid = sa.Column(sa.String(36), nullable=False, primary_key=True)
    vlan = sa.Column(sa.Integer, nullable=False, primary_key=True)
    logical_switch_uuid = sa.Column(sa.String(36), nullable=False,
                                    primary_key=True)
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False,
                                 primary_key=True)


class PendingUcastMacsRemote(model_base.BASEV2, model_base.HasId):
    __tablename__ = 'pending_ucast_macs_remotes'
    uuid = sa.Column(sa.String(36), nullable=True)
    mac = sa.Column(sa.String(32), nullable=False)
    logical_switch_uuid = sa.Column(sa.String(36), nullable=False)
    locator_uuid = sa.Column(sa.String(36), nullable=True)
    dst_ip = sa.Column(sa.String(64))
    vm_ip = sa.Column(sa.String(64))
    ovsdb_identifier = sa.Column(sa.String(64), nullable=False)
    operation = sa.Column(sa.String(8), nullable=False)
    timestamp = sa.Column(sa.DateTime, nullable=False)
