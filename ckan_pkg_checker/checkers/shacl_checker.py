import csv
import logging
from collections import namedtuple

import pandas as pd

from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
from ckan_pkg_checker.utils import rdf_utils, utils

log = logging.getLogger(__name__)

ShaclResult = namedtuple("ShaclResult", ["property", "value", "msg", "node"])


class ShaclChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the validation checker"""
        self.siteurl = siteurl
        self.csvfilename = utils.get_csvdir(rundir) / utils.get_config(
            config, "shaclchecker", "csvfile", required=True
        )
        self.statfilename = utils.get_csvdir(rundir) / utils.get_config(
            config, "shaclchecker", "statfile", required=True
        )
        shaclfile = utils.get_config(
            config, "shaclchecker", "shacl_file", required=True
        )
        frequency_file = utils.get_config(
            config, "shaclchecker", "frequency_file", required=True
        )
        self._prepare_csv_file()
        self.shacl_graph = rdf_utils.parse_rdf_graph_from_url(file=shaclfile, bind=True)
        self.ont_graph = rdf_utils.parse_rdf_graph_from_url(file=frequency_file)

    def _prepare_csv_file(self):
        self.csv_fieldnames = [
            "contact_email",
            "contact_name",
            "organization_name",
            "dataset_title",
            "dataset_url",
            "node",
            "property",
            "value",
            "severity",
            "error_msg",
            "pkg_type",
            "checker_type",
            "template",
        ]
        self.csvfile = open(self.csvfilename, "w")
        self.csvwriter = csv.DictWriter(self.csvfile, fieldnames=self.csv_fieldnames)
        self.csvwriter.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        pkg_type = pkg.get("pkg_type", utils.DCAT)
        dataset_graph = None
        if pkg.get("source_url"):
            dataset_graph = rdf_utils.get_dataset_graph_from_source(
                pkg["source_url"], pkg["identifier"]
            )
            utils.log_and_echo_msg(
                f"--> rdf graph for Dataset{pkg.get('name')} taken from harvest source"
            )
        if not dataset_graph:
            pkg_dcat_serilization_url = utils.get_pkg_dcat_serialization_url(
                self.siteurl, pkg["name"]
            )
            dataset_graph = rdf_utils.parse_rdf_graph_from_url(
                pkg_dcat_serilization_url, bind=True
            )
            utils.log_and_echo_msg(
                f"--> rdf graph for Dataset{pkg.get('name')} taken from platform"
            )
        if not dataset_graph:
            utils.log_and_echo_msg(
                f"--> rdf graph for dataset {pkg.get('name')} could not be serialized.",
                error=True,
            )
            return

        checker_results = rdf_utils.get_shacl_results(
            dataset_graph, self.shacl_graph, self.ont_graph
        )
        if not checker_results:
            utils.log_and_echo_msg(f"--> Dataset {pkg.get('name')} conforms")
        else:
            utils.log_and_echo_msg(f"--> Dataset {pkg.get('name')} does not conform")
        checker_results = list(set(checker_results))
        for shacl_result in checker_results:
            self.write_result(pkg, pkg_type, shacl_result)

    def write_result(self, pkg, pkg_type, shacl_result):
        contacts = utils.get_pkg_metadata_contacts(
            pkg.get("send_to"),
            pkg.get("contact_points"),
        )
        title = utils.get_field_in_one_language(pkg["title"], pkg["name"])
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, pkg["name"])
        organization = pkg.get("organization").get("name")
        utils.log_and_echo_msg(
            f"contacts for {pkg['name']}, pkg_type of {organization} are: {contacts}"
        )
        for contact in contacts:
            self.csvwriter.writerow(
                {
                    "contact_email": contact.email,
                    "contact_name": contact.name,
                    "organization_name": organization,
                    "dataset_title": title,
                    "dataset_url": dataset_url,
                    "node": shacl_result.node,
                    "property": shacl_result.property,
                    "value": shacl_result.value,
                    "severity": shacl_result.severity,
                    "error_msg": shacl_result.msg,
                    "pkg_type": pkg_type,
                    "checker_type": utils.MODE_SHACL,
                    "template": "shaclchecker_error.html",
                }
            )

    def finish(self):
        """Close the file"""
        self.csvfile.close()
        self._statistics()

    def _statistics(self):
        df = pd.read_csv(self.csvfilename)
        df_filtered = df.filter(["property", "value", "error_msg"])
        dg = (
            df_filtered.groupby(["error_msg"])
            .size()
            .reset_index()
            .rename(columns={0: "count"})
        )
        dg = dg.set_index("error_msg")
        msg_dict = dg.to_dict().get("count")
        statfile = open(self.statfilename, "w")
        statwriter = csv.DictWriter(statfile, fieldnames=["message", "count"])
        statwriter.writeheader()
        if self.shacl_graph:
            for message in self.shacl_graph.objects(predicate=rdf_utils.SHACL.message):
                msg = str(message)
                statwriter.writerow({"message": msg, "count": msg_dict.get(msg, 0)})

    def __repr__(self):
        return "Shacl Checker"
