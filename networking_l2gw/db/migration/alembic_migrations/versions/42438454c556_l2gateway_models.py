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

"""l2gateway_models

Revision ID: 42438454c556
Revises: 54c9c8fe22bf
Create Date: 2014-11-27 01:57:56.997665

"""

# revision identifiers, used by Alembic.
revision = '42438454c556'
down_revision = '54c9c8fe22bf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('l2gateways',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('tenant_id', sa.String(length=255),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'))

    op.create_table('l2gatewaydevices',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('device_name', sa.String(length=255),
                              nullable=False),
                    sa.Column('l2_gateway_id', sa.String(length=36),
                              nullable=False),
                    sa.ForeignKeyConstraint(['l2_gateway_id'],
                                            ['l2gateways.id'],
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'))

    op.create_table('l2gatewayinterfaces',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('interface_name', sa.String(length=255),
                              nullable=True),
                    sa.Column('segmentation_id', sa.Integer(),
                              nullable=True),
                    sa.Column('device_id', sa.String(length=36),
                              nullable=False),
                    sa.ForeignKeyConstraint(['device_id'],
                                            ['l2gatewaydevices.id'],
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'))

    op.create_table('l2gatewayconnections',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('tenant_id', sa.String(length=255),
                              nullable=True),
                    sa.Column('l2_gateway_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('network_id', sa.String(length=36),
                              nullable=False),
                    sa.Column('segmentation_id', sa.Integer(),
                              nullable=True),
                    sa.ForeignKeyConstraint(['l2_gateway_id'],
                                            ['l2gateways.id'],
                                            ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['network_id'], ['networks.id'],
                                            ondelete='CASCADE'),
                    sa.UniqueConstraint('l2_gateway_id',
                                        'network_id'),
                    sa.PrimaryKeyConstraint('id'))

    op.create_table('pending_ucast_macs_remotes',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=True),
                    sa.Column('mac', sa.String(32), nullable=False),
                    sa.Column('logical_switch_uuid', sa.String(36),
                              nullable=False),
                    sa.Column('locator_uuid', sa.String(36),
                              nullable=True),
                    sa.Column('dst_ip', sa.String(64)),
                    sa.Column('vm_ip', sa.String(64)),
                    sa.Column('ovsdb_identifier', sa.String(64),
                              nullable=False),
                    sa.Column('operation', sa.String(8), nullable=False),
                    sa.Column('timestamp', sa.DateTime, nullable=False))
