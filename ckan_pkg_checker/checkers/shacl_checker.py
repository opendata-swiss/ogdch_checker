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
        shaclexportfile = utils.get_config(
            config, "shaclchecker", "shacl_export_file", required=True
        )
        shaclimportfile = utils.get_config(
            config, "shaclchecker", "shacl_import_file", required=False
        )
        frequency_file = utils.get_config(
            config, "shaclchecker", "frequency_file", required=True
        )
        self._prepare_csv_file()
        self.shacl_export_graph = rdf_utils.parse_rdf_graph_from_url(
            file=shaclexportfile, bind=True
        )
        self.shacl_import_graph = rdf_utils.parse_rdf_graph_from_url(
            file=shaclimportfile, bind=True
        )
        self.ont_graph = rdf_utils.parse_rdf_graph_from_url(file=frequency_file)

    def _prepare_csv_file(self):
        self.csv_fieldnames = [
            "contact_email",
            "contact_name",
            "organization_name",
            "dataset_title",
            "dataset_url",
            "dataset_rdf",
            "dataset_ttl",
            "node",
            "property",
            "value",
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

        # get content from the pkg
        pkg["rdf"] = self.siteurl + "/dataset/" + pkg["name"] + ".rdf"
        pkg["ttl"] = self.siteurl + "/dataset/" + pkg["name"] + ".ttl"
        pkg_type = pkg.get("pkg_type", utils.DCAT)

        dataset_export_graph = rdf_utils.parse_rdf_graph_from_url(pkg["rdf"], bind=True)
        if self.shacl_import_graph:
            dataset_import_graph = rdf_utils.build_reduced_graph_form_package(pkg)

        if not dataset_export_graph:
            utils.log_and_echo_msg(
                f"rdf graph for dataset {pkg.get('name')} could not be serialized.",
                error=True,
            )
            return

        checker_results = rdf_utils.get_shacl_results(
            dataset_export_graph, self.shacl_export_graph, self.ont_graph
        )
        if not checker_results:
            utils.log_and_echo_msg(f"--> Dataset Export {pkg.get('name')} conforms")
        else:
            utils.log_and_echo_msg(
                f"--> Dataset Export {pkg.get('name')} does not conform"
            )
        if self.shacl_import_graph:
            dataset_import_graph = rdf_utils.build_reduced_graph_form_package(pkg)
            import_results = rdf_utils.get_shacl_results(
                dataset_import_graph, self.shacl_import_graph, self.ont_graph
            )
            if not import_results:
                utils.log_and_echo_msg(f"--> Dataset Import {pkg.get('name')} conforms")
            else:
                utils.log_and_echo_msg(
                    f"--> Dataset Import {pkg.get('name')} does not conform"
                )
                checker_results.extend(import_results)

        checker_results = list(set(checker_results))
        for shacl_result in checker_results:
            self.write_result(pkg, pkg_type, shacl_result)

    def write_result(self, pkg, pkg_type, shacl_result):
        contacts = utils.get_pkg_contacts(pkg.get("contact_points"))
        title = utils.get_field_in_one_language(pkg["title"], pkg["name"])
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, pkg["name"])
        organization = pkg.get("organization").get("name")
        for contact in contacts:
            self.csvwriter.writerow(
                {
                    "contact_email": pkg.get("send_to", contact.email),
                    "contact_name": pkg.get("send_to", contact.name),
                    "organization_name": organization,
                    "dataset_title": title,
                    "dataset_url": dataset_url,
                    "dataset_rdf": pkg.get("rdf"),
                    "dataset_ttl": pkg.get("ttl"),
                    "node": shacl_result.node,
                    "property": shacl_result.property,
                    "value": shacl_result.value,
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
        for message in self.shacl_export_graph.objects(
            predicate=rdf_utils.SHACL.message
        ):
            msg = str(message)
            statwriter.writerow({"message": msg, "count": msg_dict.get(msg, 0)})

    def __repr__(self):
        return "Shacl Checker"
