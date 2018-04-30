#!/usr/bin/python

from __future__ import print_function

import json
import shade


class Placement(object):
    def __init__(self, api_url, session):
        self.api_url = api_url
        self.session = session

    def list_resource_providers(self):
        res = self.session.get(
            self.api_url + '/resource_providers')
        return res.json().get('resource_providers', [])

    def get_resource_provider(self, uuid):
        res = self.session.get(
            self.api_url + '/resource_providers/{}'.format(uuid))
        return res.json()

    def get_resource_provider_allocations(self, uuid):
        res = self.session.get(
            self.api_url + '/resource_providers/{}/allocations'.format(uuid))
        return res.json()

cloud = shade.OpenStackCloud()
token = cloud.auth_token
placement_svc = cloud.get_service('placement')
placement_endpoint = cloud.search_endpoints(
    filters=dict(service_id=placement_svc.id, interface='public'))[0]

api_url = placement_endpoint['url']
print('using placement api @ {}'.format(api_url))

tally = {}
providers = {}
placement = Placement(api_url, cloud.keystone_session)
for provider in placement.list_resource_providers():
    providers[provider['uuid']] = provider
    allocations = placement.get_resource_provider_allocations(provider['uuid'])
    for instance_uuid, allocation in allocations['allocations'].items():
        if instance_uuid not in tally:
            tally[instance_uuid] = {}

        tally[instance_uuid][provider['uuid']] = allocation

with open('dump.json', 'w') as fd:
    json.dump({'providers': providers, 'tally': tally}, fd,
              indent=2)

for instance_uuid, allocations in tally.items():
    if len(allocations) > 1:
        print('{} has multiple allocations'.format(instance_uuid))
        instance = cloud.get_server(instance_uuid, all_projects=True)
        if instance:
            current_hypervisor = instance.get(
                'OS-EXT-SRV-ATTR:hypervisor_hostname')
        else:
            current_hypervisor = None

        for provider_uuid, allocation in allocations.items():
            provider = providers[provider_uuid]
            if provider['name'] == current_hypervisor:
                mark = '*'
            else:
                mark = '-'
            print('{} {} ({})'.format(mark,
                                      provider['name'],
                                      provider_uuid))
