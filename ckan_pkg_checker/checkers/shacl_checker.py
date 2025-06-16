import csv
import logging
from collections import namedtuple

import pandas as pd
from rdflib import Graph

from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
from ckan_pkg_checker.utils import rdf_utils, utils

log = logging.getLogger(__name__)

ShaclResult = namedtuple("ShaclResult", ["property", "value", "msg", "node"])


class ShaclChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the validation checker"""
        self.siteurl = siteurl
        runpath = utils.get_csvdir(rundir)
        self.csvfilename = runpath / utils.get_config(
            config, "shaclchecker", "csvfile", required=True
        )
        self.statfilename = runpath / utils.get_config(
            config, "shaclchecker", "statfile", required=True
        )
        self.contactsstats_filename = runpath / utils.get_config(
            config, "contacts", "statsfile", required=True
        )
        shaclfile = utils.get_config(
            config, "shaclchecker", "shacl_file", required=True
        )
        frequency_file = utils.get_config(
            config, "shaclchecker", "frequency_file", required=True
        )
        theme_file = utils.get_config(
            config, "shaclchecker", "theme_file", required=True
        )
        licenses_file = utils.get_config(
            config, "shaclchecker", "licenses_file", required=True
        )
        formats_file = utils.get_config(
            config, "shaclchecker", "formats_file", required=True
        )
        mime_types_file = utils.get_config(
            config, "shaclchecker", "mime_types_file", required=True
        )
        language_file = utils.get_config(
            config, "shaclchecker", "language_file", required=True
        )
        self._prepare_csv_file()
        self.shacl_graph = rdf_utils.parse_rdf_graph_from_url(file=shaclfile, bind=True)

        # Load and merge ontology graphs into a single RDF graph
        frequency_graph = rdf_utils.parse_rdf_graph_from_url(file=frequency_file)
        theme_graph = rdf_utils.parse_rdf_graph_from_url(file=theme_file)
        licenses_graph = rdf_utils.parse_rdf_graph_from_url(file=licenses_file)
        formats_graph = rdf_utils.parse_rdf_graph_from_url(file=formats_file)
        mime_types_graph = rdf_utils.parse_rdf_graph_from_url(file=mime_types_file)
        language_graph = rdf_utils.parse_rdf_graph_from_url(file=language_file)

        self.ont_graph = Graph()
        ont_graphs_list = [
            frequency_graph,
            theme_graph,
            licenses_graph,
            formats_graph,
            mime_types_graph,
            language_graph,
        ]
        triples_to_add = [triple for graph in ont_graphs_list for triple in graph]

        for triple in triples_to_add:
            self.ont_graph.add(triple)

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
        if pkg.get("source_url"):locals()
            dataset_graph = rdf_utils.get_dataset_graph_from_source(
                pkg["source_url"], pkg["identifier"]
            )
            utils.log_and_echo_msg(
                f"--> rdf graph for Dataset{pkg.get('name')} taken from harvest source."
            )
        if not dataset_graph:
            pkg_dcat_serilization_url = utils.get_pkg_dcat_serialization_url(
                self.siteurl, pkg["name"]
            )
            dataset_graph = rdf_utils.parse_rdf_graph_from_url(
                pkg_dcat_serilization_url, bind=True
            )
            utils.log_and_echo_msg(
                f"--> rdf graph for Dataset{pkg.get('name')} taken from platform."
            )
        if not dataset_graph:
            utils.log_and_echo_msg(
                f"--> rdf graph for dataset {pkg.get('name')} could not be serialized from harvest source.",
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
        if not checker_results:
            return
        contacts = utils.get_pkg_metadata_contacts(
            pkg.get("send_to"),
            pkg.get("contact_points"),
        )
        utils.log_and_echo_msg(
            f"contacts for {pkg['name']}, {pkg_type} of {pkg['organization'].get('name')} are: {contacts}"
        )
        for shacl_result in checker_results:
            self.write_result(pkg, pkg_type, shacl_result, contacts)

    def write_result(self, pkg, pkg_type, shacl_result, contacts):
        title = utils.get_field_in_one_language(pkg["title"], pkg["name"])
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, pkg["name"])
        organization = pkg.get("organization").get("name")
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
        utils.contacts_statistics(
            checker_result_path=self.csvfilename,
            contactsstats_filename=self.contactsstats_filename,
            checker_error_fieldname="error_msg",
        )

    def _statistics(self):
        df = pd.read_csv(self.csvfilename)
        df_filtered = df.filter(["property", "value", "error_msg"])
        # Group by both message and property name
        dg = (
            df_filtered.groupby(["error_msg", "property"])
            .size()
            .reset_index(name="count")
        )

        with open(self.statfilename, "w", newline="") as statfile:
            statwriter = csv.DictWriter(
                statfile, fieldnames=["property", "message", "count"]
            )
            statwriter.writeheader()
            for _, row in dg.iterrows():
                statwriter.writerow(
                    {
                        "property": row["property"],
                        "message": row["error_msg"],
                        "count": row["count"],
                    }
                )

    def __repr__(self):
        return "Shacl Checker"
