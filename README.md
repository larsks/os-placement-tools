The `check_placement.py` script will audit the Nova Placement API and
report on instances that have allocations on more than one hypervisor.
The report looks something like this:

    $ python check_placement.py
    acf37e22-6333-4209-8e41-c408d9544311
    * os-compute-06.example.com
    - os-compute-08.example.com
    65aaa918-a192-42d5-b292-9d9f3ae57106
    - os-compute-06.example.com
    * os-compute-09.example.com
    - os-compute-07.example.com

In the above list, the UUIDs are instance ids. `-` marks hypervisors
on which the instance is *not* running, and `*` marks the hypervisor
on which the instance is currently running.

If you pass the `--fix` option, then the script will set an explicit
allocation for each instance on its active hypervisor.  This is the
equivalent of running (if you have installed [osc-placement][]):

    openstack resource provider allocation set \
      --allocation=rp=ccb0dd44-8c80-44fb-b9c3-18da43d1d754,VCPU=2,MEMORY_MB=4096,DISK_GB=10 \
      65aaa918-a192-42d5-b292-9d9f3ae57106

[osc-placement]: https://docs.openstack.org/osc-placement/latest/cli/index.html

If you pass `--fix`, you would see, after the report listing:

    $ python check_placement.py --fix
    [...]
    WARNING:__main__:fixing allocation for acf37e22-6333-4209-8e41-c408d9544311
    WARNING:__main__:fixing allocation for 65aaa918-a192-42d5-b292-9d9f3ae57106

