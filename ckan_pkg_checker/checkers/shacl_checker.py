import csv
from configparser import ConfigParser
from collections import namedtuple
from ckan_pkg_checker.utils import utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
import ckan_pkg_checker.utils.rdf_utils as rdf_utils
import click
from pyshacl import validate
from rdflib.namespace import RDF, NamespaceManager, Namespace, SKOS
from rdflib import Graph
from pprint import pprint
from urllib.error import HTTPError, URLError

SHACL = Namespace("http://www.w3.org/ns/shacl#")
DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
SCHEMA = Namespace('http://schema.org/')
ADMS = Namespace("http://www.w3.org/ns/adms#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
TIME = Namespace('http://www.w3.org/2006/time')
LOCN = Namespace('http://www.w3.org/ns/locn#')
GSP = Namespace('http://www.opengis.net/ont/geosparql#')
OWL = Namespace('http://www.w3.org/2002/07/owl#')
SPDX = Namespace('http://spdx.org/rdf/terms#')
XML = Namespace('http://www.w3.org/2001/XMLSchema')

namespaces = {
    'dct': DCT,
    'dcat': DCAT,
    'adms': ADMS,
    'vcard': VCARD,
    'foaf': FOAF,
    'schema': SCHEMA,
    'time': TIME,
    'skos': SKOS,
    'locn': LOCN,
    'gsp': GSP,
    'owl': OWL,
    'xml': XML,
    'sh': SHACL,
}

import logging
import pprint
log = logging.getLogger(__name__)

ShaclResult = namedtuple('ShaclResult', ['property', 'value', 'msg', 'node'])


class ShaclChecker(CheckerInterface):
    def initialize(self, rundir, config, siteurl):
        """Initialize the validation checker"""
        self.siteurl = siteurl
        csvfile = utils._get_csvdir(rundir) / utils._get_config(config, 'shaclchecker', 'csvfile')
        msgfile = utils._get_msgdir(rundir) / utils._get_config(config, 'messages', 'msgfile')
        self._prepare_csv_file(csvfile)
        self._prepare_msg_file(msgfile)

        self.shacl_graph = Graph()
        self.shacl_graph.parse('ogdch.shacl.ttl')
        for k, v in namespaces.items():
            self.shacl_graph.bind(k, v)
        self.shacl_graph.namespace_manager = NamespaceManager(self.shacl_graph)

    def _prepare_csv_file(self, csvfile):
        self.csv_fieldnames = [
            'contact_email',
            'contact_name',
            'organization_name',
            'dataset_title',
            'dataset_url',
            'dataset_rdf',
            'dataset_ttl',
            'node',
            'property',
            'value',
            'msg',
        ]
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
        pkg['rdf'] = self.siteurl + '/dataset/' + pkg['name'] + '.rdf'
        pkg['ttl'] = self.siteurl + '/dataset/' + pkg['name'] + '.ttl'
        pkg_type = pkg.get('pkg_type', utils.DCAT)
        try:
            dataset_graph = Graph().parse(pkg['rdf'])
        except (HTTPError, URLError) as e:
            log.error(f"Request Error {e} occured for {pkg['rdf']}")
            return
        except Exception as e:
            log.error(f"Exception {e} of type {type(e).__name__} occured at {pkg['rdf']}")
            return
        for k, v in namespaces.items():
            dataset_graph.bind(k, v)
        dataset_graph.namespace_manager = NamespaceManager(dataset_graph)
        validation_results = validate(dataset_graph, shacl_graph=self.shacl_graph)
        conforms, results_graph, results_text = validation_results
        if not conforms:
            for k, v in namespaces.items():
                results_graph.bind(k, v)
            results_graph.namespace_manager = NamespaceManager(results_graph)
            checker_results = []
            for validation_item in results_graph.subjects(predicate=RDF.type, object=SHACL.ValidationResult):
                property_ref = rdf_utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.resultPath)
                if property_ref:
                    property = property_ref.n3(results_graph.namespace_manager)
                    node = rdf_utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.focusNode)
                    value = rdf_utils.get_object_from_graph(graph=dataset_graph, subject=node, predicate=property_ref)
                    msg = rdf_utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.resultMessage)
                    if msg:
                        msg = msg.toPython()
                shacl_result = ShaclResult(
                    node=node,
                    property=property,
                    value=value,
                    msg=msg,
                )
                checker_results.append(shacl_result)
            for shacl_result in checker_results:
                self.write_result(pkg, pkg_type, shacl_result)

    def write_result(self, pkg, pkg_type, shacl_result):
        contacts = utils._get_pkg_contacts(pkg.get('contact_points'))
        title = utils._get_field_in_one_language(pkg['title'], pkg['name'])
        dataset_url = utils._get_ckan_dataset_url(self.siteurl, pkg['name'])
        organization = pkg.get('organization').get('name')
        for contact in contacts:
            self.csvwriter.writerow(
                {'contact_email': contact.email,
                 'contact_name': contact.name,
                 'organization_name': organization,
                 'dataset_title': title,
                 'dataset_url': dataset_url,
                 'dataset_rdf': pkg.get('rdf'),
                 'dataset_ttl': pkg.get('ttl'),
                 'node': shacl_result.node,
                 'property': shacl_result.property,
                 'value': shacl_result.value,
                 'msg': shacl_result.msg,
                 })
            msg = utils._build_msg_per_shacl_result(
                dataset_url=dataset_url,
                title=title,
                node=shacl_result.node,
                property=shacl_result.property,
                value=shacl_result.value,
                shacl_msg=shacl_result.msg,
            )
            self.mailwriter.writerow({
                'contact_email': contact.email,
                'contact_name': contact.name,
                'pkg_type': pkg_type,
                'msg': msg,
            })

    def finish(self):
        """Close the file"""
        self.csvfile.close()
        self.msgfile.close()

    def __repr__(self):
        return "Shacl Checker"
