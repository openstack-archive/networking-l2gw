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

"""add indexes to tenant_id

Revision ID: 49ce408ac349
Create Date: 2016-07-22 10:42:14.495451

"""

from alembic import op

from neutron.db import migration


# revision identifiers, used by Alembic.
revision = '49ce408ac349'
down_revision = '60019185aa99'

# milestone identifier, used by neutron-db-manage
neutron_milestone = [migration.NEWTON, migration.OCATA]


def upgrade():
    for table in ['l2gateways', 'l2gatewayconnections']:
        op.create_index(op.f('ix_%s_tenant_id' % table),
                        table, ['tenant_id'], unique=False)
