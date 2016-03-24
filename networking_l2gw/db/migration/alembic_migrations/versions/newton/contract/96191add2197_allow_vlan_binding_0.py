# Copyright 2016 vikas.d-m@hpe.com/Hewlett Packard Enterprise
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

"""allow_vlan_binding_0

Revision ID: 96191add2197
Revises: 79919185aa99
Create Date: 2016-06-21 21:57:01.823502

"""

# revision identifiers, used by Alembic.
revision = '96191add2197'
down_revision = '79919185aa99'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('vlan_bindings', 'vlan', nullable=True,
                    existing_type=sa.Integer(), existing_nullable=False,
                    autoincrement=False)
