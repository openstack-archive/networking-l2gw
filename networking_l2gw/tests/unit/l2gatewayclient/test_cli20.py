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

import mock

from neutronclient import shell as neutronshell
from neutronclient.tests.unit import test_cli20 as neutron_test_cli20
from neutronclient.v2_0 import client as l2gatewayclient

TOKEN = neutron_test_cli20.TOKEN
end_url = neutron_test_cli20.end_url


class MyResp(neutron_test_cli20.MyResp):

    pass


class MyApp(neutron_test_cli20.MyApp):

    pass


class MyComparator(neutron_test_cli20.MyComparator):

    pass


class ContainsKeyValue(object):
    """Checks whether key/value pair(s) are included in a dict parameter.

    This class just checks whether specifid key/value pairs passed in
    __init__() are included in a dict parameter. The comparison does not
    fail even if other key/value pair(s) exists in a target dict.
    """

    def __init__(self, expected):
        self._expected = expected

    def __eq__(self, other):
        if not isinstance(other, dict):
            return False
        for key, value in self._expected.items():
            if key not in other:
                return False
            if other[key] != value:
                return False
        return True

    def __repr__(self):
        return ('<%s (expected: %s)>' %
                (self.__class__.__name__, self._expected))


class CLITestV20Base(neutron_test_cli20.CLITestV20Base):

    def setUp(self, plurals=None):
        super(CLITestV20Base, self).setUp()
        self.client = l2gatewayclient.Client(token=TOKEN,
                                             endpoint_url=self.endurl)

    def _test_create_resource(self, resource, cmd, name, myid, args,
                              position_names, position_values,
                              tenant_id=None, tags=None, admin_state_up=True,
                              extra_body=None, cmd_resource=None,
                              parent_id=None, **kwargs):
        if not cmd_resource:
            cmd_resource = resource
        body = {resource: {}, }
        body[resource].update(kwargs)

        for i in range(len(position_names)):
            body[resource].update({position_names[i]: position_values[i]})
        ress = {resource:
                {self.id_field: myid}, }
        if name:
            ress[resource].update({'name': name})
        resstr = self.client.serialize(ress)
        # url method body
        resource_plural = self.client.get_resource_plural(cmd_resource)
        path = getattr(self.client, resource_plural + "_path")
        mock_body = MyComparator(body, self.client)
        resp = (MyResp(200), resstr)
        with mock.patch.object(cmd, "get_client",
                               return_value=self.client), \
                mock.patch.object(self.client.httpclient, "request",
                                  return_value=resp):
            self.client.httpclient.request(
                end_url(path), 'POST',
                body=mock_body,
                headers=ContainsKeyValue(
                    {'X-Auth-Token': TOKEN}))
            cmd_parser = cmd.get_parser('create_' + resource)
            neutronshell.run_command(cmd, cmd_parser, args)
            _str = self.fake_stdout.make_string()
            self.assertIn(myid, _str)
            if name:
                self.assertIn(name, _str)
