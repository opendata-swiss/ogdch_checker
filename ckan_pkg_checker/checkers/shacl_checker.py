import csv
import logging
from collections import namedtuple
from ckan_pkg_checker.utils import utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
import click
from pyshacl import validate
from rdflib.namespace import RDF, NamespaceManager, Namespace, SKOS

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

log = logging.getLogger(__name__)

ShaclResult = namedtuple('ShaclResult', ['property', 'value', 'msg', 'node'])


class ShaclChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the validation checker"""
        self.siteurl = siteurl
        shaclfile = utils.get_config(config, 'shaclchecker', 'shacl_file', required=True)
        csvfile = utils.get_csvdir(rundir) / utils.get_config(config, 'shaclchecker', 'csvfile', required=True)
        frequency_file = utils.get_config(config, 'shaclchecker', 'frequency_file', required=True)
        self._prepare_csv_file(csvfile)
        self.shacl_graph = utils.parse_rdf_graph_from_url(file=shaclfile)
        self.ont_graph = utils.parse_rdf_graph_from_url(file=frequency_file)
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
            'error_msg',
            'pkg_type',
            'checker_type',
            'template',
        ]
        self.csvfile = open(csvfile, 'w')
        self.csvwriter = csv.DictWriter(
            self.csvfile, fieldnames=self.csv_fieldnames)
        self.csvwriter.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        pkg['rdf'] = self.siteurl + '/dataset/' + pkg['name'] + '.rdf'
        pkg['ttl'] = self.siteurl + '/dataset/' + pkg['name'] + '.ttl'
        pkg_type = pkg.get('pkg_type', utils.DCAT)
        dataset_graph = utils.parse_rdf_graph_from_url(pkg['rdf'])
        if not dataset_graph:
            return
        for k, v in namespaces.items():
            dataset_graph.bind(k, v)
        dataset_graph.namespace_manager = NamespaceManager(dataset_graph)
        validation_results = validate(dataset_graph, shacl_graph=self.shacl_graph, ont_graph=self.ont_graph)
        conforms, results_graph, results_text = validation_results
        if conforms:
            utils.log_and_echo_msg(f"--> Dataset {pkg.get('name')} conforms")
        if not conforms:
            for k, v in namespaces.items():
                results_graph.bind(k, v)
            results_graph.namespace_manager = NamespaceManager(results_graph)
            checker_results = []
            for validation_item in results_graph.subjects(predicate=RDF.type, object=SHACL.ValidationResult):
                property_ref = utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.resultPath)
                if property_ref:
                    property = property_ref.n3(results_graph.namespace_manager)
                    node = utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.focusNode)
                    value = utils.get_object_from_graph(graph=dataset_graph, subject=node, predicate=property_ref)
                    msg = utils.get_object_from_graph(graph=results_graph, subject=validation_item, predicate=SHACL.resultMessage)
                    if msg:
                        msg = msg.toPython()
                    shacl_result = ShaclResult(
                        node=node,
                        property=property,
                        value=value,
                        msg=msg,
                    )
                    utils.log_and_echo_msg(f"--> Dataset {pkg.get('name')} ShaclError {shacl_result}")
                    checker_results.append(shacl_result)
                else:
                    utils.log_and_echo_msg(f"shacl result without property ref detected at {pkg.get('name')}: {results_text}")
            for shacl_result in checker_results:
                self.write_result(pkg, pkg_type, shacl_result)

    def write_result(self, pkg, pkg_type, shacl_result):
        contacts = utils.get_pkg_contacts(pkg.get('contact_points'))
        title = utils.get_field_in_one_language(pkg['title'], pkg['name'])
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, pkg['name'])
        organization = pkg.get('organization').get('name')
        for contact in contacts:
            self.csvwriter.writerow(
                {'contact_email': pkg.get('send_to', contact.email),
                 'contact_name': pkg.get('send_to', contact.name),
                 'organization_name': organization,
                 'dataset_title': title,
                 'dataset_url': dataset_url,
                 'dataset_rdf': pkg.get('rdf'),
                 'dataset_ttl': pkg.get('ttl'),
                 'node': shacl_result.node,
                 'property': shacl_result.property,
                 'value': shacl_result.value,
                 'error_msg': shacl_result.msg,
                 'pkg_type': pkg_type,
                 'checker_type': utils.MODE_SHACL,
                 'template': 'shaclchecker_error.html',
                 })

    def finish(self):
        """Close the file"""
        self.csvfile.close()

    def __repr__(self):
        return "Shacl Checker"
