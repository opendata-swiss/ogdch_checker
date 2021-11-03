import csv
import click
from collections import namedtuple
from ckan_pkg_checker.utils import utils
import ckan_pkg_checker.utils.request_utils as request_utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface

import logging
log = logging.getLogger(__name__)

CheckResult = namedtuple('CheckResult', ['resource', 'item', 'msg'])


class LinkChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the link checker"""
        self.url_result_cache = {}
        self.siteurl = siteurl
        csvfile = utils.get_csvdir(rundir) / utils.get_config(config, 'linkchecker', 'csvfile')
        msgfile = utils.get_msgdir(rundir) / utils.get_config(config, 'messages', 'msgfile')
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
        landing_page = pkg.get('url')
        if landing_page:
            check_result = self._check_url_status(
                "landing_page_url", landing_page, pkg)
            if check_result:
                check_results.append(check_result)

        if 'relations' in pkg:
            for relation in pkg['relations']:
                relation_url = relation.get('url')
                if relation_url:
                    check_result = self._check_url_status(
                        "relations_url", relation_url, pkg)
                    if check_result:
                        check_results.append(check_result)

        for resource in pkg['resources']:
            log.info(f"LINKCHECKER: checking RESOURCE: {utils.get_field_in_one_language(resource['display_name'], '')}")
            resource_results = self._check_resource(pkg, resource)
            if resource_results:
                check_results.extend(resource_results)
        for check_result in check_results:
            self.write_result(pkg, pkg_type, check_result)

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
                'resource_url', resource_url, resource)
            if check_result:
                resource_results.append(check_result)
        if download_url and download_url != resource_url:
            check_result = self._check_url_status(
                'download_url', download_url, resource)
            if check_result:
                resource_results.append(check_result)
        return resource_results

    def _check_url_status(self, test_title, test_url, resource=None):
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
                msg=test_result, resource=resource, item=test_url)
            log.info(f"LINKCHECKER: ERROR: \n{test_title} \nURL {test_url}\nMSG {check_result.msg}")
            click.echo(f"Linkchecker Error: {test_title} url {test_url} msg {check_result.msg}")
            return check_result

    def write_result(self, pkg, pkg_type, check_result):
        contacts = utils.get_pkg_contacts(
            pkg.get('contact_points'))
        title = utils.get_field_in_one_language(
            pkg['title'], pkg['name'])
        dataset_url = utils.get_ckan_dataset_url(
            self.siteurl, pkg['name'])
        organization = pkg.get('organization').get('name')
        resource_url = ''
        if check_result.resource:
            resource_url = utils.get_ckan_resource_url(
                self.siteurl, pkg['name'],
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
            msg = utils.build_msg_per_error(
                check_result.item, check_result.msg,
                dataset_url, title, resource_url)
            self.mailwriter.writerow({
                'contact_email': pkg.get('send_to', contact.email),
                'contact_name': pkg.get('send_to', contact.name),
                'pkg_type': pkg_type,
                'msg': msg,
            })

    def __repr__(self):
        return "Link Checker"
