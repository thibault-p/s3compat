#!/usr/bin/env python

from xml.etree import ElementTree
from collections import defaultdict, Counter
from tabulate import tabulate
from copy import deepcopy
import argparse
import yaml
import sys
import csv

result_types = ('PASS', 'NEW_FAILURE', 'KNOWN_FAILURE', 'UNEXPECTED_PASS', 'SKIP',)


def dict_merge(a, b):
    if not isinstance(b, dict):
        return b

    result = deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
            result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def load_known_failures(kf_fn):
    with open(kf_fn, 'r') as kf_file:
        return yaml.load(kf_file)


def extract_message(node):
    text = node.attrib['message']
    if not text:
        return None

    end = text.find('\n')
    if end != -1:
        return text[:end]
    else:
        return text[:20] + '...'


def load_nose_xml(test_file):
    results = {}

    test_result_xml = ElementTree.parse(test_file)

    for test in test_result_xml.findall('testcase'):
        result = 'PASS'
        message = None
        name = test.attrib['classname'] + '.' + test.attrib['name']
        failures = test.findall('failure')
        errors = test.findall('error')
        skipped = test.findall('skipped')

        # TODO: Condense or differentiate
        if failures:
            assert len(failures) == 1
            message = extract_message(failures[0])
            result = 'FAIL'

        if errors:
            assert len(errors) == 1
            message = extract_message(errors[0])
            result = 'FAIL'

        if skipped:
            assert len(skipped) == 1
            result = 'SKIP'

        results[name] = dict(name=name,
                             result=result,
                             message=message,
                             time=test.attrib['time'])

    return results


def csv_report(results):
    fieldnames = ['name', 'result', 'report', 'message']
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    writer.writeheader()
    for _, row in results.iteritems():
        writer.writerow(row)


def summary_report(results, detailed):
    success = True
    by_report_status = defaultdict(list)
    for test, rec in results.iteritems():
        by_report_status[rec.get('report')].append(rec)

    by_failure_message = Counter(r['message'] for t, r in
                                 results.iteritems() if r['message'])

    if not detailed:
        table = []
        for s in ('PASS', 'NEW_FAILURE', 'KNOWN_FAILURE', 'UNEXPECTED_PASS', 'SKIP'):
            table.append((s, len(by_report_status[s])))

        print tabulate(table)
        print("TOTAL TESTS:   %d" % len(results))
        print
    print "10 most common failures:"
    print tabulate(by_failure_message.most_common(10))
    print
    print "10 longest-running tests:"
    print tabulate(
        (t, r['time']) for t, r in sorted(
            results.items(),
            key=lambda x: float(x[1]['time']),
            reverse=True)[:10])
    for status in ('NEW_FAILURE', 'UNEXPECTED_PASS'):
        if not by_report_status[status]:
            continue
        success = False
        print
        print "%s:" % status
        for test in by_report_status[status]:
            print test['name']
    return success


def result_passed(passed, total):
    # Calculate perecentage and raw totals
    return ["%.1f%%" % (float(passed)/total*100),
            '%d/%d' % (passed, total)] if total else ['N/A']


def get_row(name, elements, totals, results, codes, all_codes):
    row = [name]
    result_counter = dict.fromkeys(result_types, 0)
    current_codes = set()
    for element in elements:
        if element not in results:
            continue
        result_counter[results[element]['report']] += 1
        try:
            code = kfs[results[element]['name']]['code']
            if code in codes:
                if code not in current_codes:
                    current_codes.add(code)
        except KeyError:
            pass
        if results:
            del results[element]

    for result_type in result_types:
        row.append(result_counter[result_type])
        totals[result_type] += result_counter[result_type]

    row += result_passed(result_counter['PASS'],
                         sum(result_counter.values()))

    # Notes column, formatted for mediawiki
    code_string = ""
    for code in sorted(current_codes):
        if code not in all_codes:
            code_string = '<ref name="%s">%s</ref>' % (code, codes[code])
            all_codes.add(code)
        else:
            # Only need footnote for first instance
            code_string = '<ref name="%s"/>' % code
    row.append(code_string)

    return row


def detailed_results_table(results, detailed_attributes, custom_attributes,
                           kfs, codes):
    table = [["Category", 'Pass', 'New Failure',
              'Known Failure', 'Unexp. Pass', 'Skip', "Pass %", "Tests Passed", 'Notes']]

    totals = dict.fromkeys(result_types, 0)

    results = results.copy()
    all_codes = set()

    custom_attributes_table = []
    if custom_attributes:
        for custom_attribute in sorted(custom_attributes):
            row = get_row(custom_attribute,
                          custom_attributes[custom_attribute], totals, results,
                          codes, all_codes)
            custom_attributes_table.append(row)

    flag_table = []
    if 'flags' in detailed_attributes:
        for flag in sorted(detailed_attributes['flags']):
            row = get_row(flag, detailed_attributes['flags'][flag],
                          totals, results, codes, all_codes)
            if row[5] != 'N/A':
                flag_table.append(row)

    for method in sorted(detailed_attributes['method'], key=str.lower):
        for resource in sorted(detailed_attributes['resource'], key=str.lower):
            intersection = (detailed_attributes['method'][method].
                            intersection(detailed_attributes['resource']
                            [resource]))
            if intersection:
                old_length = len(results)
                row = get_row("%s %s" % (method, resource), intersection,
                              totals, results, codes, all_codes)
                if old_length - len(results):
                    table.append(row)

    table += flag_table
    table += custom_attributes_table
    row = get_row("other", results.copy(), totals, results, codes, all_codes)
    if row[5] != 'N/A':
        table.append(row)

    table.append(["Total"] + (list(totals[result_type] for result_type
                              in result_types) + result_passed(totals['PASS'],
                              sum(totals.values())))+[None])

    return table


def detailed_report_console(results, detailed_attributes, custom_attributes,
                            kfs, codes):
    table = detailed_results_table(results, detailed_attributes,
                                   custom_attributes, kfs, codes)
    # Hide Notes column, and only show new failure/known failure/unexp. pass/skip if there's data
    columns = (True, True, None, None, None, None, True, True, False)
    table = [[v for i, v in enumerate(row)
             if (table[-1][i] if columns[i] is None
                 else columns[i])] for row in table]
    print tabulate(table, headers="firstrow", tablefmt='simple')


def detailed_report_wiki(results, detailed_attributes, custom_attributes, kfs,
                         codes):
    table = detailed_results_table(results, detailed_attributes,
                                   custom_attributes, kfs, codes)
    columns = (True, False, False, False, False, True, True, True)

    table = [[v for i, v in enumerate(row) if columns[i]] for row in table]

    print ('== Amazon S3 REST API Compatability using '
           '[https://github.com/ceph/s3-tests Ceph s3-tests] ==')
    print tabulate(table, headers="firstrow", tablefmt='mediawiki')
    print "<references />"


parser = argparse.ArgumentParser()
parser.add_argument('-f', '--format', choices=['summary', 'csv'],
                    help='output format', default='summary')
parser.add_argument('-d', '--detailed',
                    help='output detailed information using attribute file')
parser.add_argument('-c', '--custom',
                    help='use custom attributes')
parser.add_argument('-df', '--detailedformat', choices=['console', 'wiki'],
                    help='output detailed information format',
                    default='console')
parser.add_argument('-kf', '--known-failures', action='append',
                    help='known-failure file', default=[])
parser.add_argument('test_results',
                    help='test result file')
args = parser.parse_args()

results = load_nose_xml(args.test_results)

all_kfs = {}
for kf in args.known_failures:
    all_kfs = dict_merge(all_kfs, load_known_failures(kf))

kfs = all_kfs.get('ceph_s3', {})
for test, rec in results.iteritems():
    rec['report'] = 'PASS'

    if rec['result'] == 'SKIP':
        rec['report'] = 'SKIP'
        continue

    if test not in kfs:
        if rec['result'] == 'FAIL':
            rec['report'] = 'NEW_FAILURE'
        continue

    if rec['result'] == 'FAIL':
        status = kfs[test]['status']
        if status == 'KNOWN':
            rec['report'] = 'KNOWN_FAILURE'
    else:
        rec['report'] = 'UNEXPECTED_PASS'

codes = all_kfs.get('codes', {})

custom_attributes = {}
if args.custom:
    try:
        with open(args.custom, 'r') as cf:
            custom_load = yaml.load(cf)['tests']
    except IOError:
        print 'Unable to open custom attributes file'
        raise
    for test in custom_load:
        attrib_cat = custom_load[test]['category']

        if attrib_cat:
            cur_attr = custom_attributes.get(attrib_cat, None)
            if cur_attr is None:
                cur_attr = set()
                custom_attributes[attrib_cat] = cur_attr
            cur_attr.add(test)

detailed_attributes = {}
if args.detailed:
    try:
        with open(args.detailed, 'r') as yaml_loading:
            detailed_attributes = yaml.load(yaml_loading)
    except IOError:
        print 'Unable to open detailed results attribute file'
        raise

if args.custom or args.detailed:
    if args.detailedformat == 'console':
        detailed_report_console(results, detailed_attributes,
                                custom_attributes, kfs, codes)
    elif args.detailedformat == 'wiki':
        detailed_report_wiki(results, detailed_attributes, custom_attributes,
                             kfs, codes)
    else:
        # We should never get here -- argparse should catch errors
        raise ValueError("format must be 'console' or 'wiki'")

if args.format == 'summary':
    if not summary_report(results, args.detailed):
        exit(1)
elif args.format == 'csv':
    csv_report(results)
else:
    # We should never get here -- argparse should catch errors
    raise ValueError("format must be 'summary' or 'csv'")
