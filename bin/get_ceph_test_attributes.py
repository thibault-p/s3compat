#!/usr/bin/env python
import collections
import nose
import os
import yaml


ATTRS = ('resource', 'method', 'operation', 'assertion')
FLAGS = ('100_continue', 'multiregion', 'versioning')


def get_test_info(directory):
    q = collections.deque(nose.loader.TestLoader().loadTestsFromDir('.'))
    while q:
        x = q.popleft()
        if isinstance(x, nose.suite.ContextSuite):
            q.extend(x._tests)
        elif isinstance(x, nose.case.Test):
            info = {'module': x.test.test.__module__,
                    'name': x.test.test.__name__,
                    'full_name': '.'.join(x.test.address()[1:]),
                    'flags': []}
            info.update((a, getattr(x.test.test, a))
                        for a in ATTRS if hasattr(x.test.test, a))
            info['flags'].extend(f for f in FLAGS if hasattr(x.test.test, f))
            yield info
        else:
            raise TypeError(type(x))


# Get tests from proper directory
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

os.environ['S3TEST_CONF'] = os.path.join(repo_root, 'config', 'ceph-s3.cfg')

attributes = {a: {} for a in ATTRS}
attributes['flags'] = {}

for info in get_test_info(os.path.join(repo_root, "ceph-tests")):
    for attr in ATTRS:
        if attr not in info:
            continue
        attributes[attr].setdefault(info[attr].lower(), set())
        attributes[attr][info[attr].lower()].add(info['full_name'])
    for f in info['flags']:
        attributes['flags'].setdefault(f, set())
        attributes['flags'][f].add(info['full_name'])

# Save test attributes
with open(os.path.join(repo_root, 'output', 'ceph-s3.out.yaml'), 'w') as fp:
    yaml.dump(attributes, fp)
