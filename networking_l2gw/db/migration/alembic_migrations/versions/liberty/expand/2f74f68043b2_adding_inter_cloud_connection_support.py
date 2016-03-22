# Copyright 2016 <PUT YOUR NAME/COMPANY HERE>
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

"""Adding inter-cloud connection support

Revision ID: 2f74f68043b2
Revises: 79919185aa99
Create Date: 2016-01-19 13:33:20.411698

"""

# from neutron.db.migration import cli
#
# # revision identifiers, used by Alembic.
revision = '2f74f68043b2'
down_revision = '60019185aa99'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('l2remotegateways',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('ipaddr', sa.String(length=255),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'))

    op.create_table('l2remotegatewayconnections',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('gateway', sa.String(length=36), nullable=False),
                    sa.Column('network', sa.String(length=36), nullable=False),
                    sa.Column('remote_gateway',
                              sa.String(length=36),
                              nullable=False),
                    sa.Column('seg_id', sa.String(length=255),
                              nullable=True),
                    sa.Column('flood', sa.String(length=5),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id'))

    op.add_column('physical_locators',
                  sa.Column('tunnel_key', sa.Integer(), nullable=True))
