from collections import namedtuple
from string import Template
from urllib.error import HTTPError, URLError

from pyshacl import validate
from rdflib import BNode, Graph, Literal
from rdflib.namespace import DCTERMS as DCT
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

ShaclResult = namedtuple(
    "ShaclResult", ["property", "value", "msg", "node", "severity"]
)


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
            return
    if not graph and file:
        try:
            graph = Graph().parse(file)
        except Exception as e:
            log_and_echo_msg(
                f"Exception {e} of type {type(e).__name__} occured at {url}"
            )
            return
    if graph and bind:
        for k, v in namespaces.items():
            graph.bind(k, v)
        graph.namespace_manager = NamespaceManager(graph)
    return graph


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
                graph=results_graph, subject=validation_item,
                predicate=SHACL.value
            ) or get_object_from_graph(
                graph=dataset_graph, subject=node, predicate=property_ref
            )
            if type(value) == BNode:
                try:
                    for p, o in dataset_graph.predicate_objects(subject=value):
                        p_qname = dataset_graph.compute_qname(p)
                        value = f"{p_qname[0]}:{p_qname[2]} {o}"
                except Exception as e:
                    log_and_echo_msg(
                        f"""Exception {e} of type {type(e).__name__} 
                        BNode value could not be determined for {property}"""
                    )
                    pass
            severity = get_object_from_graph(
                graph=results_graph,
                subject=validation_item,
                predicate=SHACL.resultSeverity,
            )
            severity = results_graph.compute_qname(severity)[2]
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
                severity=severity,
            )
            checker_results.append(shacl_result)
    return checker_results


def get_dataset_graph_from_source(source_url, identifier):
    try:
        source = Graph().parse(source_url, format="application/rdf+xml")
    except Exception as e:
        log_and_echo_msg(
            f"Exception {e} happened for source_url {source_url} and {identifier}"
        )
        return None

    for prefix, ns in namespaces.items():
        source.bind(prefix, ns)
    source.namespace_manager = NamespaceManager(source)

    dataset = Graph()
    for prefix, ns in namespaces.items():
        dataset.bind(prefix, ns)
    dataset.namespace_manager = NamespaceManager(dataset)

    # If identifier has @org, also try to match just the base hash
    raw_id = identifier.split("@")[0] if "@" in identifier else identifier

    dataset_refs = set()

    for subj in source.subjects(predicate=DCT.identifier):
        for obj in source.objects(subject=subj, predicate=DCT.identifier):
            obj_str = str(obj)
            if obj_str == identifier or obj_str == raw_id:
                dataset_refs.add(subj)

    if not dataset_refs:
        log_and_echo_msg(
            f"No RDF subjects with dct:identifier == '{identifier}' or '{raw_id}' found in {source_url}"
        )
        return None

    for ref in dataset_refs:
        for pred, obj in source.predicate_objects(subject=ref):
            dataset.add((ref, pred, obj))
            # Add second-level triples
            if isinstance(obj, (str, Literal)):
                continue
            for subpred, subobj in source.predicate_objects(subject=obj):
                dataset.add((obj, subpred, subobj))

    return dataset
