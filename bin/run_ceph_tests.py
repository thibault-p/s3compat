#!/usr/bin/env python
import nose
import os
import sys

os.environ['S3TEST_CONF'] = '../config/ceph-s3.cfg'

base = os.path.basename(__file__)

# Run tests from proper directory
test_root = ""
if os.path.exists("../bin/"+base):
    test_root = "../"
elif os.path.exists("bin/"+base):
    test_root = "./"

os.chdir(os.path.join(test_root, "ceph-tests"))

# Run full tests
sys.argv = (sys.argv[:1] +
            ['--with-xunit', '--xunit-file=../output/ceph-s3.out.xml'] +
            sys.argv[1:])
if not nose.run():
    exit(1)
