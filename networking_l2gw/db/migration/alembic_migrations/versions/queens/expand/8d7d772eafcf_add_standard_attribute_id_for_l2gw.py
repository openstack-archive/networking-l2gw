# Copyright 2017 <PUT YOUR NAME/COMPANY HERE>
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

"""add standard_attribute_id for l2gw

Revision ID: 8d7d772eafcf
Revises: 49ce408ac349
Create Date: 2017-12-19 07:49:23.362289

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8d7d772eafcf'
down_revision = '49ce408ac349'

TABLES = ("l2gateways", "l2gatewayconnections", "l2gatewaydevices")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column('standard_attr_id', sa.BigInteger(),
                                       nullable=True))
