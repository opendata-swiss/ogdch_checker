import random
import sys
import click
import logging
from datetime import datetime
from collections import namedtuple
from urllib.parse import urljoin
from string import ascii_lowercase
from configparser import NoSectionError, NoOptionError


Contact = namedtuple('Contact', ['name', 'email'])
FieldNamesMsgFile = ['contact_email', 'contact_name', 'pkg_type', 'msg']
FieldNamesContactFile = ['contact_email', 'contact_name', 'dataset', 'pkg_type']
GEOCAT = 'geocat'
DCAT = 'dcat'
MODE_SHACL = 'shacl'
MODE_LINK = 'link'
MODE_ALL = 'all'
SITE_ABNAHME = 'https://ckan.ogdch-abnahme.clients.liip.ch'
SITE_TEST = 'https://ckan.ogdch-test.clients.liip.ch'
SITE_PROD = 'https://ckan.opendata.swiss'
map_siteurl_to_instance = {
    SITE_PROD: 'prod',
    SITE_ABNAHME: 'abnahme',
    SITE_TEST: 'test,'
}


def _get_ckan_resource_url(ckan_siteurl, pkg_name, resource_id):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name + '/resource/' + resource_id) # noqa


def _get_ckan_dataset_url(ckan_siteurl, pkg_name):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name)


def _build_msg_per_contact(receiver_name):
    msg = f'Hello {receiver_name} <br><br>\n\n'

    msg += '[DE] - Wir haben ein Problem festgestellt beim Versuch, auf folgende Quellen zuzugreifen.<br>\n' # noqa
    msg += 'Bitte kontrollieren Sie, ob diese Quellen noch zug&auml;nglich sind und korrigieren Sie sie n&ouml;tigenfalls.<br><br>\n\n' # noqa

    msg += '[FR] - Nous avons constat&eacute; un probl&egrave;me en essayant d&#39;acc&eacute;der aux ressources suivantes.<br>\n' # noqa
    msg += 'Merci de v&eacute;rifier si ces ressources sont toujours disponibles et de les corriger si n&eacute;cessaire.<br><br>\n\n' # noqa

    msg += '[IT] - Abbiamo riscontrato un problema nel tentativo di accedere alle risorse seguenti.<br>\n' # noqa
    msg += 'La preghiamo di verificare se le risorse sono ancora disponibili e, se necessario, correggerle.<br><br>\n\n' # noqa

    msg += '[EN] - While accessing the following resources, we found some unexpected behaviour.<br>\n' # noqa
    msg += 'Please check if those resources are still available.<br><br>\n\n'

    msg += '-----<br><br>\n\n'
    return msg


def _build_msg_per_error(test_url, error_msg, dataset_url, title, resource_url=None):
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


def _build_msg_per_shacl_result(dataset_url, title, node, property, value, shacl_msg):
    msg = f"Dataset: <a href='{dataset_url}'>{title}</a>\n"
    msg += f"A Validation Error occured"
    if node:
        msg += f" at: <a href='{node}'>{node}</a>"
    msg += f"\nProperty '{property}': {shacl_msg}\n"
    if value:
        msg += f" Value received: {value}"
    msg += "<br><br>\n\n-----<br><br>\n\n"
    return msg


def _get_field_in_one_language(multi_language_field, backup):
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


def _get_email_subject():
    return 'opendata.swiss : Automatische Kontrolle der Quellen / Controle automatique des ressources / Controllo automatico delle risorse / automatic ressource checker' # noqa


def _get_pkg_contacts(pkg_contact_points):
    recipients = []
    for contact in pkg_contact_points:
        recipients.append(Contact(email=contact['email'], name=contact['name'])) # noqa
    return recipients


def _get_runname(org, pkg, mode, limit, siteurl):
    name_parts = []
    name_parts.append(datetime.now().strftime("%Y%m%d-%H%M"))
    if siteurl:
        name_parts.append(map_siteurl_to_instance.get(siteurl))
    if mode:
        name_parts.append(f"{mode}")
    if org:
        name_parts.append(f"org-{org[:10]}")
    if pkg:
        name_parts.append(f"pkg-{pkg[:10]}")
    if limit:
        name_parts.append(f"limit-{limit}")
    runname = '-'.join(name_parts)
    click.echo(runname)
    return runname


def _get_csvdir(rundir):
    return rundir / 'csv'


def _get_msgdir(rundir):
    return rundir / 'msgs'


def _get_maildir(rundir):
    return rundir / 'mails'


def _get_logdir(rundir):
    return rundir / 'logs'


def _make_dirs(tmpdir, runname):
    rundir = tmpdir / runname
    try:
        rundir.mkdir()
    except Exception as e:
        click.echo(f"An Error {e} occured:\n"
                   f"The specified tmp directory {rundir} does not exist.\n"
                   f"Please set it up and run again.")
        sys.exit()
    maildir = _get_maildir(rundir)
    maildir.mkdir()
    logdir = _get_logdir(rundir)
    logdir.mkdir()
    csvdir = _get_csvdir(rundir)
    csvdir.mkdir()
    msgdir = _get_msgdir(rundir)
    msgdir.mkdir()
    return rundir


def _process_msg_file_name(filename):
    components = filename.split('#')
    contact_type = components[0]
    contact_email = '#'.join(components[1:])
    return contact_type, contact_email


def _get_config(config, section, option):
    try:
       value = config.get(section, option)
    except NoSectionError:
        raise click.UsageError(f"Configuration: Section '{section}' is missing.")
    except NoOptionError:
        raise click.UsageError(f"Configuration:  Section '{section}' is missing the option '{option}'.")
    return value


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


def _get_run_info(org, pkg, limit):
    if org:
        return f"Organization: {org}"
    elif pkg:
        return f"Dataset: {pkg}"
    elif limit:
        return f"Limit: {limit}"
    return "Full run"
