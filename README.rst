===============
networking-l2gw
===============

API's and implementations to support L2 Gateways in Neutron.

* Free software: Apache license
* Source: https://git.openstack.org/cgit/openstack/networking-l2gw

L2 Gateways
-----------

This project proposes a Neutron API extension that can be used to express
and manage L2 Gateway components. In the simplest terms L2 Gateways are meant
to bridge two or more networks together to make them look at a single L2
broadcast domain.

Initial implementation
----------------------

There are a number of use cases that can be addressed by an L2 Gateway API.
Most notably in cloud computing environments, a typical use case is bridging
the virtual with the physical. Translate this to Neutron and the OpenStack
world, and this means relying on L2 Gateway capabilities to extend Neutron
logical (overlay) networks into physical (provider) networks that are outside
the OpenStack realm. These networks can be, for instance, VLAN's that may or
may not be managed by OpenStack.

More information
----------------

For help using or hacking on L2GW, you can send an email to the
`OpenStack Development Mailing List <mailto:openstack-dev@lists.openstack.org>`;
please use the [L2-Gateway] Tag in the subject. Most folks involved hang out on
the IRC channel #openstack-neutron.

Getting started
---------------

* TODO
