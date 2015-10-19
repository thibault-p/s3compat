
About
---------------------------

s3compat is a project to gather useful ways of measuring the level of S3 compatability provided by the
OpenStack Swift object store (primarily through the Swift3[1] middleware).  It is intended to wrap around
other test suites and provide information and tools for executing these suites, reporting on the results,
and tracking progress toward the goal of full(er) S3 compatibility.

At present it is centered around the ceph-s3 tests, but we will add other test suites based around real
use cases at a later date.

Installation
---------------------------

This instructions are based on Ubuntu 14.04 LTS

  1. Install virtualenv and create one for this project. [Not strictly necessary, but recommended]
  1. Update git submodules

    ```
    git submodule update --init
    ```

  2. Install package-based dependencies through your package manager, e.g.:

    ```
    sudo apt-get install libyaml-dev libevent-dev
    ```

  3. Install python dependencies:

    ```
    pip install -r requirements.txt
    pip install -r ceph-tests/requirements.txt
    ```

  4. Create a configuration file

    ```
    cp config/ceph-s3.cfg.SAMPLE config/ceph-s3.cfg
    ```

  5. Edit values for the Swift cluster and users to suit the Swift cluster you are using


Execution
---------------------------

To run the ceph-s3 tests, run

    bin/run_ceph_tests.py

The xml output file will be placed in "./output/ceph-s3.out.xml".

Reporting
---------------------------

Generate test attributes file:

    bin/get_ceph_test_attributes.py

The yaml test attributes will be stored in output/ceph-s3.out.yaml


Generate detailed report:

    ./bin/report.py -d output/ceph-s3.out.yaml -df console output/ceph-s3.out.xml


Generate report with mediawiki formatted table:

    ./bin/report.py -d output/ceph-s3.out.yaml -df wiki output/ceph-s3.out.xml


Generate detailed report with custom attributes:

    ./bin/report.py -d output/ceph-s3.out.yaml -df console output/ceph-s3.out.xml -c data/classification_sample.yaml

A sample custom attribute file is providing, classifying ceph-s3 tests into categories.

