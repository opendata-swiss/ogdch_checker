from collections import namedtuple
from urllib.error import HTTPError, URLError

from pyshacl import validate
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import RDF, SKOS, Namespace, NamespaceManager

from ckan_pkg_checker.utils.utils import log_and_echo_msg

SHACL = Namespace("http://www.w3.org/ns/shacl#")
DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
SCHEMA = Namespace("http://schema.org/")
ADMS = Namespace("http://www.w3.org/ns/adms#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
TIME = Namespace("http://www.w3.org/2006/time")
LOCN = Namespace("http://www.w3.org/ns/locn#")
GSP = Namespace("http://www.opengis.net/ont/geosparql#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
XML = Namespace("http://www.w3.org/2001/XMLSchema")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

namespaces = {
    "dct": DCT,
    "dcat": DCAT,
    "adms": ADMS,
    "vcard": VCARD,
    "foaf": FOAF,
    "schema": SCHEMA,
    "time": TIME,
    "skos": SKOS,
    "locn": LOCN,
    "gsp": GSP,
    "owl": OWL,
    "xml": XML,
    "sh": SHACL,
    "rdf": RDF,
}

ShaclResult = namedtuple("ShaclResult", ["property", "value", "msg", "node"])


def get_object_from_graph(graph, subject, predicate):
    objects = []
    for item in graph.objects(subject=subject, predicate=predicate):
        objects.append(item)
    if objects:
        return objects[0]
    return None


def parse_rdf_graph_from_url(url=None, file=None, bind=False):
    graph = None
    if url:
        try:
            graph = Graph().parse(url)
        except (HTTPError, URLError) as e:
            log_and_echo_msg(f"Request Error {e} occured for {url}")
        except Exception as e:
            log_and_echo_msg(
                f"Exception {e} of type {type(e).__name__} occured at {url}"
            )
    if not graph and file:
        try:
            graph = Graph().parse(file)
        except Exception as e:
            log_and_echo_msg(
                f"Exception {e} of type {type(e).__name__} occured at {url}"
            )
    if bind:
        graph = bind_namespaces(graph)
    return graph


def build_reduced_graph_form_package(pkg):
    graph = Graph()
    dataset_ref = BNode()
    graph = bind_namespaces(graph)
    graph.add((dataset_ref, RDF.type, DCAT.Dataset))
    frequency = pkg.get('accrual_periodicity')
    if frequency:
       graph.add((dataset_ref, DCT.accrualPeriodicity, URIRef(frequency)))
    return graph


def bind_namespaces(g):
    for k, v in namespaces.items():
        g.bind(k, v)
    g.namespace_manager = NamespaceManager(g)
    return g


def get_shacl_results(dataset_graph, shacl_graph, ont_graph):
    validation_results = validate(
        dataset_graph, shacl_graph=shacl_graph, ont_graph=ont_graph
    )
    conforms, results_graph, results_text = validation_results
    if conforms:
        return []
    checker_results = []
    for validation_item in results_graph.subjects(
            predicate=RDF.type, object=SHACL.ValidationResult
    ):
        property_ref = get_object_from_graph(
            graph=results_graph,
            subject=validation_item,
            predicate=SHACL.resultPath,
        )
        if property_ref:
            property = property_ref.n3(results_graph.namespace_manager)
            node = get_object_from_graph(
                graph=results_graph,
                subject=validation_item,
                predicate=SHACL.focusNode,
            )
            value = get_object_from_graph(
                graph=dataset_graph, subject=node, predicate=property_ref
            )
            msg = get_object_from_graph(
                graph=results_graph,
                subject=validation_item,
                predicate=SHACL.resultMessage,
            )
            if msg:
                msg = msg.toPython()
            shacl_result = ShaclResult(
                node=node,
                property=property,
                value=value,
                msg=msg,
            )
            checker_results.append(shacl_result)
    return checker_results
