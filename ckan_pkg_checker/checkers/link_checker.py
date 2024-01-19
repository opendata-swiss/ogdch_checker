import csv
import json
import logging
from collections import namedtuple

import click
import pandas as pd
import requests

import ckan_pkg_checker.utils.request_utils as request_utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)

CheckResult = namedtuple("CheckResult", ["resource_id", "item", "msg", "test_title"])
TEST_ACCESS_URL = "dcat:accessURL"
TEST_RELATION_URL = "dct:relation"
TEST_QUALIFIED_RELATION_URL = "dcat:qualifiedRelation"
TEST_LANDING_PAGE_URL = "dcat:landingPage"
TEST_PUBLISHER_URL = "dct:publisher"
TEST_CONFORMS_TO_URL = "dct:conformsTo"
TEST_DOCUMENTATION_URL = "foaf:page"
TEST_DOWNLOAD_URL = "dcat:downloadURL"
TEST_RESOURCE_DOCUMENTATION_URL = "foaf:page"
TEST_ACCESS_SERVICES_URL = "dcat:accessService"
link_checks = [
    TEST_ACCESS_URL,
    TEST_RELATION_URL,
    TEST_QUALIFIED_RELATION_URL,
    TEST_LANDING_PAGE_URL,
    TEST_PUBLISHER_URL,
    TEST_CONFORMS_TO_URL,
    TEST_DOCUMENTATION_URL,
    TEST_DOWNLOAD_URL,
    TEST_RESOURCE_DOCUMENTATION_URL,
    TEST_ACCESS_SERVICES_URL,
]


class LinkChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the link checker"""
        self.url_result_cache = {}
        self.siteurl = siteurl
        runpath = utils.get_csvdir(rundir)
        self.csvfilepath = runpath / utils.get_config(
            config, "linkchecker", "csvfile", required=True
        )
        self.statfilepath = runpath / utils.get_config(
            config, "linkchecker", "statfile", required=True
        )
        self.contactsstats_filename = runpath / utils.get_config(
            config, "contacts", "statsfile", required=True
        )
        self._prepare_csv_file()

    def _prepare_csv_file(self):
        self.csv_fieldnames = [
            "contact_email",
            "contact_name",
            "organization_name",
            "test_url",
            "error_message",
            "dataset_title",
            "dataset_url",
            "resource_url",
            "test_title",
            "pkg_type",
            "checker_type",
            "template",
        ]
        self.csvfile = open(self.csvfilepath, "w")
        self.csvwriter = csv.DictWriter(self.csvfile, fieldnames=self.csv_fieldnames)
        self.csvwriter.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        pkg_type = pkg.get("pkg_type", utils.DCAT)
        check_results = []

        # Check landing page URL
        self._check_url(pkg, "url", TEST_LANDING_PAGE_URL, check_results)

        # Check publisher URL - mandatory field
        # exm.,'publisher':'{
        # "url": "https://www.ur.ch/departemente/58", "name": "Justizdirektion Kt. Uri"
        # }'
        if isinstance(pkg.get("publisher"), str):
            try:
                # parse the string into a dictionary
                pkg["publisher"] = json.loads(pkg["publisher"])
            except json.JSONDecodeError:
                log.error("Error decoding JSON for 'publisher'")

        self._check_url(pkg["publisher"], "url", TEST_PUBLISHER_URL, check_results)

        # Check relations URL
        if "relations" in pkg:
            self._check_url_from_list_dict(
                pkg["relations"], "url", TEST_RELATION_URL, check_results
            )

        # Check qualified relations URL
        if "qualified_relations" in pkg:
            self._check_url_from_list_dict(
                pkg["qualified_relations"],
                "relation",
                TEST_QUALIFIED_RELATION_URL,
                check_results,
            )

        # Check conforms to URLs
        if "conforms_to" in pkg:
            self._check_url_from_list(
                pkg, "conforms_to", TEST_CONFORMS_TO_URL, check_results
            )

        # Check documentation URLs
        if "documentation" in pkg:
            self._check_url_from_list(
                pkg, "documentation", TEST_DOCUMENTATION_URL, check_results
            )

        for resource in pkg["resources"]:
            log.info(
                f"LINKCHECKER: checking RESOURCE: {utils.get_field_in_one_language(resource['display_name'], '')}"
            )
            resource_results = self._check_resource(pkg, resource)
            if resource_results:
                check_results.extend(resource_results)
        if not check_results:
            return
        contacts = utils.get_pkg_metadata_contacts(
            pkg.get("send_to"),
            pkg.get("contact_points"),
        )
        utils.log_and_echo_msg(
            f"contacts for {pkg['name']}, {pkg_type} of {pkg['organization'].get('name')} are: {contacts}"
        )
        for check_result in check_results:
            self.write_result(pkg, pkg_type, check_result, contacts)

    def finish(self):
        self.csvfile.close()
        self._statistics()
        utils.contacts_statistics(
            checker_result_path=self.csvfilepath,
            contactsstats_filename=self.contactsstats_filename,
            checker_error_fieldname="error_message",
        )

    def _check_url(self, pkg, key, test_title, check_results):
        """Verify a single URL"""
        url = pkg.get(key)
        if url:
            check_result = self._check_url_status(test_title, url)
            if check_result:
                check_results.append(check_result)

    def _check_url_from_list(self, pkg, key, test_title, check_results):
        """Verify URLs within the list"""
        urls = pkg.get(key)
        if urls:
            for url in urls:
                if url:
                    check_result = self._check_url_status(test_title, url)
                    if check_result:
                        check_results.append(check_result)

    def _check_url_from_list_dict(self, list_dict, key, test_title, check_results):
        """Verify URLs within the list of dictionaries"""
        for dict in list_dict:
            url = dict.get(key)
            if url:
                check_result = self._check_url_status(test_title, url)
                if check_result:
                    check_results.append(check_result)

    def _check_resource_url(self, url, test_title, resource_id, resource_results):
        """Verify a single resource URL"""
        check_result = self._check_url_status(test_title, url, resource_id)
        if check_result:
            resource_results.append(check_result)

    def _check_resource_url_from_list(
        self, urls, test_title, resource_id, resource_results
    ):
        """Verify resource URLs within the list"""
        for url in urls:
            if url:
                check_result = self._check_url_status(test_title, url, resource_id)
                if check_result:
                    resource_results.append(check_result)

    def _check_resource(self, pkg, resource):
        """Check one resource"""
        resource_results = []
        access_url = resource["url"]
        try:
            download_url = resource["download_url"]
        except KeyError:
            download_url = None
            pass
        if access_url:
            self._check_resource_url(
                url=access_url,
                test_title=TEST_ACCESS_URL,
                resource_id=resource["id"],
                resource_results=resource_results,
            )

        if download_url and download_url != access_url:
            self._check_resource_url(
                url=download_url,
                test_title=TEST_DOWNLOAD_URL,
                resource_id=resource["id"],
                resource_results=resource_results,
            )

        # Check documentation URLs for the resources
        if "documentation" in resource:
            self._check_resource_url_from_list(
                urls=resource.get("documentation"),
                test_title=TEST_RESOURCE_DOCUMENTATION_URL,
                resource_id=resource["id"],
                resource_results=resource_results,
            )

        # Check documentation URLs for the resources
        if "access_services" in resource:
            self._check_resource_url_from_list(
                urls=resource.get("access_services"),
                test_title=TEST_ACCESS_SERVICES_URL,
                resource_id=resource["id"],
                resource_results=resource_results,
            )
        return resource_results

    def _check_url_status(self, test_title, test_url, resource_id=None):
        """Check one url"""
        if test_url in self.url_result_cache:
            test_result = self.url_result_cache[test_url]
        else:
            # check first as 'HEAD', then as 'GET'
            test_result = request_utils.check_url_status(test_url)
            if test_result:
                test_result = request_utils.check_url_status(
                    test_url, http_method="GET"
                )
            self.url_result_cache[test_url] = test_result
        if test_result:
            check_result = CheckResult(
                msg=test_result,
                resource_id=resource_id,
                item=test_url,
                test_title=test_title,
            )
            log.info(
                f"LINKCHECKER: ERROR: \n{test_title} \nURL {test_url}\nMSG {check_result.msg}"
            )
            click.echo(
                f"Linkchecker Error: {test_title} url {test_url} msg {check_result.msg}"
            )
            return check_result

    def write_result(self, pkg, pkg_type, check_result, contacts):
        title = utils.get_field_in_one_language(pkg["title"], pkg["name"])
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, pkg["name"])
        organization = pkg.get("organization").get("name")
        resource_url = ""
        if check_result.resource_id:
            resource_url = utils.get_ckan_resource_url(
                self.siteurl, pkg["name"], check_result.resource_id
            )
        for contact in contacts:
            self.csvwriter.writerow(
                {
                    "contact_email": contact.email,
                    "contact_name": contact.name,
                    "organization_name": organization,
                    "test_url": check_result.item,
                    "error_message": check_result.msg,
                    "dataset_title": title,
                    "dataset_url": dataset_url,
                    "resource_url": resource_url,
                    "test_title": check_result.test_title,
                    "pkg_type": pkg_type,
                    "checker_type": utils.MODE_LINK,
                    "template": "linkchecker_error.html",
                }
            )

    def _statistics(self):
        df = pd.read_csv(self.csvfilepath)
        df_filtered = df.filter(["test_title"])
        df_filtered.rename(columns={"test_title": "message"}, inplace=True)
        dg = (
            df_filtered.groupby(["message"])
            .size()
            .reset_index()
            .rename(columns={0: "count"})
        )
        dg = dg.set_index("message")
        msg_dict = dg.to_dict().get("count")
        statfile = open(self.statfilepath, "w")
        statwriter = csv.DictWriter(statfile, fieldnames=["message", "count"])
        statwriter.writeheader()
        for check in link_checks:
            count = msg_dict.get(check, 0)
            statwriter.writerow({"message": check, "count": count})

    def __repr__(self):
        return "Link Checker"
