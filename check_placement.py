#!/usr/bin/python

from __future__ import print_function

import argparse
import json
import logging
import os_client_config
import shade
import sys

LOG = logging.getLogger(__name__)
cloud_config = os_client_config.OpenStackConfig()


class Placement(object):
    def __init__(self, cloud):
        self.cloud = cloud
        self.session = cloud.keystone_session

        self.lookup_endpoint()

    def lookup_endpoint(self):
        placement_svc = self.cloud.get_service('placement')
        placement_endpoint = self.cloud.search_endpoints(
            filters=dict(service_id=placement_svc.id, interface='public'))[0]

        placement_url = placement_endpoint['url']
        LOG.info('using placement api @ {}'.format(placement_url))
        self.placement_url = placement_url

    def list_resource_providers(self):
        res = self.session.get(
            self.placement_url + '/resource_providers')
        return res.json().get('resource_providers', [])

    def get_resource_provider(self, uuid):
        res = self.session.get(
            self.placement_url + '/resource_providers/{}'.format(uuid))
        return res.json()

    def get_resource_provider_allocations(self, uuid):
        res = self.session.get(
            self.placement_url +
            '/resource_providers/{}/allocations'.format(uuid))
        return res.json()


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument('--fix', action='store_true')
    p.add_argument('--dry-run', '-n', action='store_true')

    g = p.add_argument_group('Logging')
    g.add_argument('--debug', action='store_const',
                   const='DEBUG', dest='loglevel')
    g.add_argument('--verbose', '-v', action='store_const',
                   const='INFO', dest='loglevel')

    cloud_config.register_argparse_arguments(p, sys.argv)

    p.set_defaults(loglevel='WARNING')
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)

    cloud = cloud_config.get_one_cloud(argparse=args)
    cloud_api = shade.OpenStackCloud(cloud_config=cloud)
    placement = Placement(cloud_api)

    tally = {}
    providers = {}

    LOG.info('getting resource allocations')
    for provider in placement.list_resource_providers():
        providers[provider['uuid']] = provider
        allocations = (
            placement.get_resource_provider_allocations(provider['uuid']))
        for instance_uuid, allocation in allocations['allocations'].items():
            if instance_uuid not in tally:
                tally[instance_uuid] = {}

            tally[instance_uuid][provider['uuid']] = allocation

    multiple = {}

    LOG.info('auditing allocations')
    for instance_uuid, allocations in tally.items():
        if len(allocations) > 1:
            LOG.info('{} has multiple allocations'.format(instance_uuid))
            instance = cloud_api.get_server(instance_uuid, all_projects=True)
            if instance:
                current_hypervisor = instance.get(
                    'OS-EXT-SRV-ATTR:hypervisor_hostname')
            else:
                current_hypervisor = None

            multiple[instance_uuid] = {
                'uuid': instance_uuid,
                'active': current_hypervisor,
                'allocations': [],
            }

            for provider_uuid, allocation in allocations.items():
                provider = providers[provider_uuid]
                if provider['name'] == current_hypervisor:
                    active = True
                else:
                    active = False

                multiple[instance_uuid]['allocations'].append({
                    'provider': provider,
                    'active': active,
                    'allocation': allocation,
                })

    with open('allocations.json', 'w') as fd:
        json.dump(multiple, fd, indent=2)

    for instance_uuid, info in multiple.items():
        print(instance_uuid)
        for allocation in info['allocations']:
            mark = '*' if allocation['active'] else '-'
            print('{} {}'.format(mark, allocation['provider']['name']))


if __name__ == '__main__':
    main()
