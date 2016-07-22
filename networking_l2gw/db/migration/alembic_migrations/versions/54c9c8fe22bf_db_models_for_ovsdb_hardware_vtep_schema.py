# Copyright 2015 OpenStack Foundation
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
#

"""DB_Models_for_OVSDB_Hardware_VTEP_Schema

Revision ID: 54c9c8fe22bf
Revises: 42438454c556
Create Date: 2015-01-27 02:05:21.599215

"""

# revision identifiers, used by Alembic.
revision = '54c9c8fe22bf'
down_revision = 'start_networking_l2gw'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('physical_locators',
                    sa.Column('dst_ip', sa.String(length=64), nullable=True),
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('physical_switches',
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('tunnel_ip', sa.String(length=64),
                              nullable=True),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.Column('switch_fault_status', sa.String(length=32),
                              nullable=True),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('physical_ports',
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('physical_switch_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.Column('port_fault_status', sa.String(length=32),
                              nullable=True),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('logical_switches',
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('key', sa.Integer(), nullable=True),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('ucast_macs_locals',
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('mac', sa.String(length=32), nullable=True),
                    sa.Column('logical_switch_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('physical_locator_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('ip_address', sa.String(length=64),
                              nullable=True),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('ucast_macs_remotes',
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('mac', sa.String(length=32), nullable=True),
                    sa.Column('logical_switch_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('physical_locator_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('ip_address', sa.String(length=64),
                              nullable=True),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.PrimaryKeyConstraint('uuid', 'ovsdb_identifier'))

    op.create_table('vlan_bindings',
                    sa.Column('port_uuid', sa.String(length=36),
                              nullable=False),
                    sa.Column('vlan', sa.Integer(), nullable=False),
                    sa.Column('logical_switch_uuid', sa.String(length=36),
                              nullable=False),
                    sa.Column('ovsdb_identifier', sa.String(length=64),
                              nullable=False),
                    sa.PrimaryKeyConstraint('port_uuid', 'ovsdb_identifier',
                                            'vlan', 'logical_switch_uuid'))
