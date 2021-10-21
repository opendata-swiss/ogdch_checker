import csv
import click
from configparser import ConfigParser
from collections import namedtuple
from ckan_pkg_checker.utils import utils
import ckan_pkg_checker.utils.request_utils as request_utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface

import logging
log = logging.getLogger(__name__)

CheckResult = namedtuple('CheckResult', ['pkg', 'resource', 'item', 'msg'])


class LinkChecker(CheckerInterface):
    def initialize(self, rundir, configpath):
        """Initialize the link checker"""
        self.url_result_cache = {}
        config = ConfigParser()
        config.read(configpath)
        self.siteurl = config.get('site', 'siteurl')
        csvfile = \
            utils._get_csvdir(rundir) / config.get('linkchecker', 'csvfile')
        msgfile = \
            utils._get_csvdir(rundir) / config.get('linkchecker', 'msgfile')
        self._prepare_csv_file(csvfile)
        self._prepare_msg_file(msgfile)

    def _prepare_csv_file(self, csvfile):
        self.csv_fieldnames = [
            'contact_email',
            'contact_name',
            'organization_name',
            'test_url',
            'error_message',
            'dataset_title',
            'dataset_url',
            'resource_url']
        self.csvfile = open(csvfile, 'w')
        self.csvwriter = csv.DictWriter(
            self.csvfile, fieldnames=self.csv_fieldnames)
        self.csvwriter.writeheader()

    def _prepare_msg_file(self, msgfile):
        self.msgfile = open(msgfile, 'w')
        self.mailwriter = csv.DictWriter(
            self.msgfile, fieldnames=utils.FieldNamesMsgFile)
        self.mailwriter.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        pkg_type = pkg.get('pkg_type', utils.DCAT)
        check_results = []
        landing_page = pkg['url']
        if landing_page:
            check_result = self._check_url_status(
                "landing_page_url", landing_page, pkg)
            if check_result:
                check_results.append(check_result)

        if 'relations' in pkg:
            for relation in pkg['relations']:
                relation_url = relation['url']
                if relation_url:
                    check_result = self._check_url_status(
                        "relations_url", relation_url, pkg)
                    if check_result:
                        check_results.append(check_result)

        for resource in pkg['resources']:
            log.info("LINKCHECKER: checking RESOURCE: {}".format(
                utils._get_field_in_one_language(resource['display_name'], '')
            ))
            resource_results = self._check_resource(pkg, resource)
            if resource_results:
                check_results.extend(resource_results)
        for result in check_results:
            self.write_result(pkg_type, result)

    def finish(self):
        self.csvfile.close()
        self.msgfile.close()

    def _check_resource(self, pkg, resource):
        """Check one resource"""
        resource_results = []
        resource_url = resource['url']
        try:
            download_url = resource['download_url']
        except KeyError:
            download_url = None
            pass
        if resource_url:
            check_result = self._check_url_status(
                'resource_url', resource_url, pkg, resource)
            if check_result:
                resource_results.append(check_result)
        if download_url and download_url != resource_url:
            check_result = self._check_url_status(
                'download_url', download_url, pkg, resource)
            if check_result:
                resource_results.append(check_result)
        return resource_results

    def _check_url_status(self, test_title, test_url, pkg, resource=None):
        """Check one url"""
        if test_url in self.url_result_cache:
            test_result = self.url_result_cache[test_url]
        else:
            # check first as 'HEAD', then as 'GET'
            test_result = request_utils.check_url_status(test_url)
            if test_result:
                test_result = request_utils.check_url_status(
                    test_url, http_method='GET')
            self.url_result_cache[test_url] = test_result
        if test_result:
            check_result = CheckResult(
                msg=test_result, pkg=pkg,
                resource=resource, item=test_url)
            log.info("LINKCHECKER: ERROR: \n{} \nURL {}\nMSG {}".format(
                test_title, test_url, check_result.msg))
            click.echo("Linkchecker Error: {} url {} msg {}".format(
                test_title, test_url, check_result.msg
            ))
            return check_result

    def write_result(self, pkg_type, check_result):
        contacts = utils.get_pkg_contacts(
            check_result.pkg.get('contact_points'))
        title = utils._get_field_in_one_language(
            check_result.pkg['title'], check_result.pkg['name'])
        dataset_url = utils._get_ckan_dataset_url(
            self.siteurl, check_result.pkg['name'])
        organization = check_result.pkg.get('organization').get('name')
        resource_url = ''
        if check_result.resource:
            resource_url = utils._get_ckan_resource_url(
                self.siteurl, check_result.pkg['name'],
                check_result.resource['id'])
        for contact in contacts:
            self.csvwriter.writerow(
                {'contact_email': contact.email,
                 'contact_name': contact.name,
                 'organization_name': organization,
                 'test_url': check_result.item,
                 'error_message': check_result.msg,
                 'dataset_title': title,
                 'dataset_url': dataset_url,
                 'resource_url': resource_url})
            msg = utils._build_msg_per_error(
                check_result.item, check_result.msg,
                dataset_url, title, resource_url)
            self.mailwriter.writerow({
                'contact_email': contact.email,
                'contact_name': contact.name,
                'pkg_type': pkg_type,
                'msg': msg,
            })

    def __repr__(self):
        return "Link Checker"
