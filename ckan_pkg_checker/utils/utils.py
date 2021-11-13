import csv
import sys
import click
import logging
import configparser
from rdflib import Graph
from datetime import datetime
from collections import namedtuple
from urllib.parse import urljoin
from configparser import NoSectionError, NoOptionError
from urllib.error import HTTPError, URLError
from pathlib import Path
from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader('ckan_pkg_checker', 'email_templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

log = logging.getLogger(__name__)
Contact = namedtuple('Contact', ['name', 'email'])
ContactKey = namedtuple('ContactKey', ['organization', 'pkg_type'])
RunParms = namedtuple('runParms', ['siteurl',
                                   'org', 'pkg', 'limit',
                                   'config', 'tmpdir', 'rundir',
                                   'mode', 'check', 'build', 'send', 'test'])
FieldNamesMsgFile = ['contact_email', 'contact_name', 'pkg_type', 'checker_type', 'msg']
GEOCAT = 'geocat'
DCAT = 'dcat'
MODE_SHACL = 'shacl'
MODE_LINK = 'link'

def get_ckan_resource_url(ckan_siteurl, pkg_name, resource_id):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name + '/resource/' + resource_id)  # noqa


def get_ckan_dataset_url(ckan_siteurl, pkg_name):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name)


def build_msg_per_contact(receiver_name, checker_type, pkg_type):
    contact_template = env.get_template('contact.html')
    html = contact_template.render(
        context={
            'receiver_name': receiver_name,
            'checker_type': checker_type,
            'pkg_type': pkg_type,
            'pkg_type_geocat': GEOCAT,
            'checker_type_shacl': MODE_SHACL,
            'checker_type_link': MODE_LINK,
        })
    return html


def _add_geocat_msg(msg, geocat_msg):
    msg += geocat_msg
    return msg


def _build_linkchecker_msg_per_contact():
    msg_de = '[DE] - Wir haben ein Problem festgestellt beim Versuch, auf folgende Quellen zuzugreifen.<br>\n'  # noqa
    msg_de += 'Bitte kontrollieren Sie, ob diese Quellen noch zug&auml;nglich sind und korrigieren Sie sie n&ouml;tigenfalls.<br><br>\n\n'  # noqa

    msg_fr = '[FR] - Nous avons constat&eacute; un probl&egrave;me en essayant d&#39;acc&eacute;der aux ressources suivantes.<br>\n'  # noqa
    msg_fr += 'Merci de v&eacute;rifier si ces ressources sont toujours disponibles et de les corriger si n&eacute;cessaire.<br><br>\n\n'  # noqa

    msg_it = '[IT] - Abbiamo riscontrato un problema nel tentativo di accedere alle risorse seguenti.<br>\n'  # noqa
    msg_it += 'La preghiamo di verificare se le risorse sono ancora disponibili e, se necessario, correggerle.<br><br>\n\n'  # noqa

    msg_en = '[EN] - While accessing the following resources, we found some unexpected behaviour.<br>\n'  # noqa
    msg_en += 'Please check if those resources are still available.<br><br>\n\n'
    return {
        'de': msg_de,
        'fr': msg_fr,
        'it': msg_it,
        'en': msg_en}


def _build_validation_msg_per_contact():
    msg_de = '[DE] - Fehlerhafte Metadaten.<br>\n'
    msg_de += 'Nachfolgende Felder Ihrer Datasets auf opendata.swiss entsprechen nicht den Anforderungen von DCAT-AP CH. Bitte ergänzen Sie die entsprechenden Angaben.<br><br>\n\n'  # noqa

    msg_fr = '[FR] - Nous avons constat&eacute; un probl&egrave;me en essayant d&#39;acc&eacute;der aux ressources suivantes.<br>\n'  # noqa
    msg_fr += 'Merci de v&eacute;rifier si ces ressources sont toujours disponibles et de les corriger si n&eacute;cessaire.<br><br>\n\n'  # noqa

    msg_it = '[IT] - Abbiamo riscontrato un problema nel tentativo di accedere alle risorse seguenti.<br>\n'  # noqa
    msg_it += 'La preghiamo di verificare se le risorse sono ancora disponibili e, se necessario, correggerle.<br><br>\n\n'  # noqa

    msg_en = '[EN] - While accessing the following resources, we found some unexpected behaviour.<br>\n'  # noqa
    msg_en += 'Please check if those resources are still available.<br><br>\n\n'
    return {
        'de': msg_de,
        'fr': msg_fr,
        'it': msg_it,
        'en': msg_en}


def _add_geocat_msg_per_contact(msgs_dict):
    msgs_dict['de'] += f"Geometadaten sind in <a href='{GEOCAT_URLS['de']}'>geocat.ch</a> zu aktualisieren."
    msgs_dict['fr'] += f"Les géométadonnées doivent être mises à jour dans <a href='{GEOCAT_URLS['fr']}'>geocat.ch</a>."
    msgs_dict['it'] += f"I geometadati devono essere attualizzati in <a href='{GEOCAT_URLS['it']}'>geocat.ch</a>."
    msgs_dict['en'] += f"Geometadata need to be updated in <a href='{GEOCAT_URLS['en']}'>geocat.ch</a>"
    return msgs_dict


def build_msg_per_error(test_url, error_msg, dataset_url, title, resource_url=None):
    msg = f"Dataset: <a href='{dataset_url}'>{title}</a>"
    if resource_url:
        resource_url = resource_url
        msg += f" (<a href='{resource_url}'>resource detail page</a>) <br>\n"
        msg += f'Accessed URL: {test_url} <br>\n'
    else:
        msg += '<br>\n'
        msg += f'Relation URL: {test_url} <br>\n'
    msg += f'Error Message: {error_msg} <br><br>\n\n-----<br><br>\n\n'
    return msg


def build_msg_per_shacl_result(dataset_url, title, node, property, value, shacl_msg):
    msg = f"Dataset: <a href='{dataset_url}'>{title}</a>\n"
    msg += "A Validation Error occured"
    if node:
        msg += f" at: <a href='{node}'>{node}</a>"
    msg += f"\nProperty '{property}': {shacl_msg}\n"
    if value:
        msg += f"Value received: '{value}'"
    msg += "<br><br>\n\n-----<br><br>\n\n"
    return msg


def get_field_in_one_language(multi_language_field, backup):
    if multi_language_field.get('de'):
        return multi_language_field['de']
    elif multi_language_field.get('fr'):
        return multi_language_field['fr']
    elif multi_language_field.get('en'):
        return multi_language_field['en']
    elif multi_language_field.get('it'):
        return multi_language_field['it']
    else:
        return backup


def get_email_subject():
    return 'opendata.swiss : Automatische Kontrolle der Quellen / Controle automatique des ressources / Controllo automatico delle risorse / automatic ressource checker'  # noqa


def get_pkg_contacts(pkg_contact_points):
    recipients = []
    for contact in pkg_contact_points:
        recipients.append(Contact(email=contact['email'], name=contact['name']))  # noqa
    return recipients


def get_csvdir(rundir):
    return rundir / 'csv'


def get_msgdir(rundir):
    return rundir / 'msgs'


def get_maildir(rundir):
    return rundir / 'mails'


def get_logdir(rundir):
    return rundir / 'logs'


def process_msg_file_name(filename):
    components = filename.split('#')
    contact_type = components[0]
    contact_email = '#'.join(components[1:])
    return contact_type, contact_email


def get_config(config, section, option, required=False, fallback=None):
    value = ''
    try:
        value = config.get(section, option)
    except NoSectionError:
        if required:
            raise click.UsageError(f"Configuration: Section '{section}' is missing.")
    except NoOptionError:
        if required:
            raise click.UsageError(f"Configuration:  Section '{section}' is missing the option '{option}'.")
    if not value and required:
        raise click.UsageError(f"Configuration value for '[{section}] {option}' is missing. Please enter it in "
                               "the configuration file. See --help"
                               " for more information.")
    if not value and fallback:
        return fallback
    return value


def set_up_contact_mapping(config):
    contact_file = get_config(config, 'contacts', 'csvfile', fallback=None)
    contact_dict = {}
    if contact_file:
        try:
            with open(contact_file, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not row.get('organization_slug') or not row.get('pkg_type') or not row.get('contact_email'):
                        continue
                    contact_key = ContactKey(organization=row['organization_slug'], pkg_type=row['pkg_type'])
                    contact_dict[contact_key] = row['contact_email']
        except FileNotFoundError:
            raise click.UsageError("'contacts.csv' file configured, but file was not found.")
        except AttributeError:
            raise click.UsageError("'contacts.csv' file configured, but file has "
                                   "not the correct format")
    return contact_dict


def get_object_from_graph(graph, subject, predicate):
    objects = []
    for item in graph.objects(subject=subject, predicate=predicate):
        objects.append(item)
    if objects:
        return objects[0]
    return None


def parse_rdf_graph_from_url(url=None, file=None):
    graph = None
    if url:
        try:
            graph = Graph().parse(url)
        except (HTTPError, URLError) as e:
            log_and_echo_msg(f"Request Error {e} occured for {url}")
        except Exception as e:
            log_and_echo_msg(f"Exception {e} of type {type(e).__name__} occured at {url}")
    if not graph and file:
        try:
            graph = Graph().parse(file)
        except Exception as e:
            log_and_echo_msg(f"Exception {e} of type {type(e).__name__} occured at {url}")
    return graph


def log_and_echo_msg(msg, error=False):
    if error:
        msg = f"\nERROR: {msg}\n"
        log.error(msg)
    else:
        log.info(msg)
    click.echo(f"{msg}")


def set_runparms(org, limit, pkg, run, configpath, build, send, mode, test):
    config = configparser.ConfigParser()
    config.read(configpath)
    if not config.sections():
        raise click.UsageError(f"Configuration could not be read from file '{configpath}'. Make"
                               f"sure that the fill exists and contains a configuration such as provided"
                               f"in 'config.ini.dist'")
    nr_scope_options = len([opt for opt in [limit, pkg, org] if opt])
    if len([opt for opt in [limit, pkg, org] if opt]) > 1:
        raise click.UsageError("Only one of the options --org, --limit, "
                               "--pkg can be used.")
    check = False
    if run:
        if nr_scope_options or mode:
            raise click.UsageError("--rundir can only be used with "
                                   "--build and --send:\n"
                                   "it implies that the check has "
                                   "already been performed "
                                   "and just the emails\n"
                                   "should be build and send out")
    else:
        if mode and mode not in [MODE_SHACL, MODE_LINK]:
            raise click.UsageError(f"--mode can only contain {MODE_SHACL} or {MODE_LINK}")
        siteurl = get_config(config, 'site', 'siteurl', required=True)
        check = True
        run = _get_runname(org=org, limit=limit, pkg=pkg, mode=mode)
    tmpdir = Path(get_config(config, 'tmpdir', 'tmppath', required=True))
    rundir = _make_dirs(tmpdir=tmpdir, runname=run)
    runparms = RunParms(siteurl=siteurl,
                        org=org, pkg=pkg, limit=limit,
                        config=config, tmpdir=tmpdir, rundir=rundir,
                        mode=mode, check=check, build=build, send=send, test=test)
    logdir = get_logdir(rundir)
    loglevel = get_config(config, 'logging', 'level', fallback='INFO')
    _setup_loggers(logdir, loglevel)
    _log_run_parms(runparms)
    return runparms


def _log_run_parms(runparms):
    info = "Run of pkg_checker:\n-------------------\n"
    for name, value in runparms._asdict().items():
        if name == 'config':
            for section in runparms.config.sections():
                for (key, val) in runparms.config.items(section):
                    info += f"[{section}] {key}={val}\n"
        else:
            info += f"{name}: {value}\n"
    log.info(info)
    info += f"Find output at {runparms.rundir}"
    click.echo(info)


def _setup_loggers(logdir, loglevel):
    logging.basicConfig(
        filename=logdir / 'package-checker.log',
        format='%(asctime)s %(levelname)s %(message)s',
        level=loglevel,
        filemode='a+'
    )
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d\n%(message)s')
    errlog = logging.FileHandler(logdir / 'package-checker.errors.log')
    errlog.setFormatter(formatter)
    errlog.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(errlog)


def _make_dirs(tmpdir, runname):
    rundir = tmpdir / runname
    try:
        rundir.mkdir()
    except Exception as e:
        click.echo(f"An Error {e} occured:\n"
                   f"The specified tmp directory {rundir} does not exist.\n"
                   f"Please set it up and run again.")
        sys.exit()
    maildir = get_maildir(rundir)
    maildir.mkdir()
    logdir = get_logdir(rundir)
    logdir.mkdir()
    csvdir = get_csvdir(rundir)
    csvdir.mkdir()
    msgdir = get_msgdir(rundir)
    msgdir.mkdir()
    return rundir


def _get_runname(org, pkg, mode, limit):
    name_parts = []
    name_parts.append(datetime.now().strftime("%Y%m%d-%H%M"))
    if mode:
        name_parts.append(f"{mode}")
    if org:
        name_parts.append(f"org-{org[:10]}")
    if pkg:
        name_parts.append(f"pkg-{pkg[:10]}")
    if limit:
        name_parts.append(f"limit-{limit}")
    runname = '-'.join(name_parts)
    return runname
