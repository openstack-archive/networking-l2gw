# Copyright (c) 2014 OpenStack Foundation
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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class API(object):
    def __init__(self, context):
        self.context = context

    @abc.abstractmethod
    def transaction(self, check_error=False, log_errors=True, **kwargs):
        """Create a transaction

        :param check_error: Allow the transaction to raise an exception?
        :type check_error:  bool
        :param log_errors:  Log an error if the transaction fails?
        :type log_errors:   bool
        :returns: A new transaction
        :rtype: :class:`Transaction`
        """

    @abc.abstractmethod
    def db_find(self, table, *conditions, **kwargs):
        """Create a command to return find OVSDB records matching conditions

        :param table:     The OVS table to query
        :type table:      string
        :param conditions:The conditions to satisfy the query
        :type conditions: 3-tuples containing (column, operation, match)
                          Type of 'match' parameter MUST be identical to column
                          type
                          Examples:
                              atomic: ('tag', '=', 7)
                              map: ('external_ids' '=', {'iface-id': 'xxx'})
                              field exists?
                                  ('external_ids', '!=', {'iface-id', ''})
                              set contains?:
                                  ('protocols', '{>=}', 'OpenFlow13')
                          See the ovs-vsctl man page for more operations
        :param columns:   Limit results to only columns, None means all columns
        :type columns:    list of column names or None
        :returns:         :class:`Command` with [{'column', value}, ...] result
        """

    @abc.abstractmethod
    def get_physical_sw_list(self):
        """Create a command to list Physical Switches."""
