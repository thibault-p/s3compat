#!/usr/bin/env python
import nose
import os
import sys
from cStringIO import StringIO
import contextlib
import yaml
import importlib

os.environ['S3TEST_CONF'] = '../config/ceph-s3.cfg'

base = os.path.basename(__file__)

# Run tests from proper directory
test_root = ""
if os.path.exists("../bin/"+base):
    test_root = "../"
elif os.path.exists("bin/"+base):
    test_root = "./"

os.chdir(os.path.join(test_root, "ceph-tests"))


# Run nose to collect test function names, suppresss output.
@contextlib.contextmanager
def capture_output():
    oldstderr = sys.stderr
    try:
        sys.stderr = StringIO()
        yield sys.stderr
    finally:
        sys.stderr = oldstderr

with capture_output() as out:
    nose.run(argv=[base, '--collect-only', '-v'])

# Get attributes of each function, and store them by
# name.  Have a set for each unique attribute value
# and save it to a file to be used for reporting later
nose_output = out.getvalue().split('\n')

indices = ('resource', 'method', 'operation', 'assertion')
flags = ('100_continue', 'multiregion', 'versioning')
attributes = {}

for index in indices:
    attributes[index] = {}

attributes['flags'] = {}

for flag in flags:
    attributes['flags'][flag] = set()

for line in nose_output:
    if not line:
        break
    full_function = line.split(' ')[0]
    full_split = full_function.split('.')
    size = len(full_split)
    while size > 1:
        size -= 1
        try:
            module_name = ".".join(full_split[:size])
            module = importlib.import_module(module_name)
            cur_funct = getattr(module, '.'.join(full_split[size:]))
        except (ImportError, AttributeError) as e:
            continue
        break

    for index in indices:
        if hasattr(cur_funct, index):
            current_attribute_value = getattr(cur_funct, index).lower()
            if current_attribute_value not in attributes[index]:
                attributes[index][current_attribute_value] = set()
            attributes[index][current_attribute_value].add(full_function)

    for flag in flags:
        if hasattr(cur_funct, flag):
            attributes['flags'][flag].add(full_function)

# Save test attributes
with open('../output/ceph-s3.out.yaml', 'w') as output:
    # pickle.dump(attributes, output)
    yaml.dump(attributes, output)
