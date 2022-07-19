import configparser
import csv
import logging
import os
import sys
from collections import defaultdict, namedtuple
from configparser import NoOptionError, NoSectionError
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import ckanapi
import click
import pandas as pd
from dotenv import dotenv_values, load_dotenv
from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("ckan_pkg_checker", "email_templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

log = logging.getLogger(__name__)
Contact = namedtuple("Contact", ["name", "email"])
ContactKey = namedtuple("ContactKey", ["organization", "pkg_type"])
RunParms = namedtuple(
    "runParms",
    [
        "siteurl",
        "org",
        "pkg",
        "limit",
        "config",
        "apikey",
        "tmpdir",
        "rundir",
        "mode",
        "check",
        "build",
        "send",
        "test",
    ],
)
FieldNamesMsgFile = ["contact_email", "contact_name", "pkg_type", "checker_type", "msg"]
GEOCAT = "geocat"
DCAT = "dcat"
STATISTICS = "statistics"
CONTACTS_STATISTICS = "contacts-statistics"
MODE_SHACL = "shacl"
MODE_LINK = "link"
modes = [MODE_LINK, MODE_SHACL]
EMAIL_SUBJECT_SHACL = "opendata.swiss : Fehlerhafte Metadaten / Métadonnées erronées / Metadati errati / Incorrect metadata"
EMAIL_SUBJECT_LINK = (
    "opendata.swiss : Fehlerhafte URLs / URL erronées / URL errati / Incorrect URLs"
)
EMAIL_SUBJECT_STATISTICS_SHACL = "opendata.swiss : Shacl Checker Validation Results"
EMAIL_SUBJECT_STATISTICS_LINK = "opendata.swiss : Link Checker Validation Results"


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def get_ckan_resource_url(ckan_siteurl, pkg_name, resource_id):
    return urljoin(
        ckan_siteurl, "/dataset/" + pkg_name + "/resource/" + resource_id
    )  # noqa


def get_ckan_dataset_url(ckan_siteurl, pkg_name):
    return urljoin(ckan_siteurl, "/dataset/" + pkg_name)


def build_msg_per_contact(receiver_name, checker_type, pkg_type):
    contact_template = env.get_template("contact.html")
    html = contact_template.render(
        context={
            "receiver_name": receiver_name,
            "checker_type": checker_type,
            "pkg_type": pkg_type,
            "pkg_type_geocat": GEOCAT,
            "checker_type_shacl": MODE_SHACL,
            "checker_type_link": MODE_LINK,
        }
    )
    return html


def build_statistics_email(receiver_name, mode, statistics):
    stat_template = env.get_template("statistics.html")
    display_checks = []
    display_errors = []
    index = 0
    for message, count in statistics.get("count").items():
        index += 1
        display_checks.append({"check_nr": index, "message": message})
        if count > 0:
            display_errors.append({"check_nr": index, "count": count})
    html = stat_template.render(
        context={
            "receiver_name": receiver_name,
            "mode": mode,
            "checks": display_checks,
            "errors": display_errors,
        }
    )
    return html


def build_contacts_statistics_email(receiver_name, mode, df_statistics):
    stat_template = env.get_template("contact_statistics.html")
    organization_results = list()
    for _, row in df_statistics.iterrows():
        organization_results.append(
            {
                "organization_name": row["organization_name"],
                "pkg_type": row["pkg_type"],
                "contact_emails": row["contact_emails"],
                "error_count": row["error_count"],
            }
        )
    html = stat_template.render(
        context={
            "receiver_name": receiver_name,
            "mode": mode,
            "rows": organization_results,
        }
    )
    return html


def build_msg_per_error(row):
    error_template = env.get_template(row["template"])
    html = error_template.render(context={"row": row})
    return html


def get_field_in_one_language(multi_language_field, backup):
    if multi_language_field.get("de"):
        return multi_language_field["de"]
    elif multi_language_field.get("fr"):
        return multi_language_field["fr"]
    elif multi_language_field.get("en"):
        return multi_language_field["en"]
    elif multi_language_field.get("it"):
        return multi_language_field["it"]
    else:
        return backup


def get_email_subject(mode):
    if mode == MODE_SHACL:
        return EMAIL_SUBJECT_SHACL
    if mode == MODE_LINK:
        return EMAIL_SUBJECT_LINK


def get_email_subject_statistics(mode):
    if mode == MODE_SHACL:
        return EMAIL_SUBJECT_STATISTICS_SHACL
    if mode == MODE_LINK:
        return EMAIL_SUBJECT_STATISTICS_LINK


def get_pkg_contacts(pkg_contact_points):
    recipients = []
    for contact in pkg_contact_points:
        recipients.append(Contact(email=contact["email"], name=contact["name"]))  # noqa
    return recipients


def get_csvdir(rundir):
    return rundir / "csv"


def get_maildir(rundir):
    return rundir / "mails"


def get_logdir(rundir):
    return rundir / "logs"


def process_msg_file_name(filename):
    filename = filename.replace(".html", "")
    components = filename.split("#")
    contact_type = components[0]
    contact_email = "#".join(components[1:])
    return contact_type, contact_email


def get_config(config, section, option, required=False, fallback=None):
    value = ""
    try:
        value = config.get(section, option)
    except NoSectionError:
        if required:
            raise click.UsageError(f"Configuration: Section '{section}' is missing.")
    except NoOptionError:
        if required:
            raise click.UsageError(
                f"Configuration:  Section '{section}' is missing the option '{option}'."
            )
    if not value and required:
        raise click.UsageError(
            f"Configuration value for '[{section}] {option}' is missing. Please enter it in "
            "the configuration file. See --help"
            " for more information."
        )
    if not value and fallback:
        return fallback
    return value


def _get_parent_organization_dict(organizatons):
    parents = {
        org.get("name"): [parent.get("name") for parent in org.get("groups")]
        for org in organizatons
    }
    return parents


def _get_organization_list(ogdremote):
    try:
        organizations = ogdremote.action.organization_list(
            all_fields=True, include_groups=True, include_dataset_count=False
        )
        return _get_parent_organization_dict(organizations)
    except ckanapi.errors.NotFound:
        log_and_echo_msg(f"No organization found for id: {id}")
    except ckanapi.errors.CKANAPIError:
        log_and_echo_msg(f"CKAN Api Error for Organization: {id}")
    return []


def _get_organization_admin_userids(ogdremote, organization_name):
    try:
        result = ogdremote.action.member_list(
            id=organization_name, object_type="user", capacity="admin"
        )
        return [member[0] for member in result]
    except ckanapi.errors.NotFound:
        log_and_echo_msg(f"No organization found for id: {organization_name}")
    except ckanapi.errors.CKANAPIError:
        log_and_echo_msg(f"CKAN Api Error for Organization: {organization_name}")


def _get_organization_admin_emails(ogdremote, userids):
    useremails = []
    for userid in userids:
        try:
            result = ogdremote.action.user_show(id=userid)
            email = result.get("email")
            if email:
                useremails.append(email)
        except ckanapi.errors.NotFound:
            log_and_echo_msg(f"No organization found for id: {userid}")
        except ckanapi.errors.CKANAPIError:
            log_and_echo_msg(f"CKAN Api Error for Organization: {userid}")
    return useremails


def set_up_contact_mapping(config, ogdremote):
    organization_with_parents = _get_organization_list(ogdremote)
    contact_dict = _get_contacts_from_file(config)
    dcat_admin_email = get_config(config, "emailsender", "dcat_admin", required=True)
    for organization_name in organization_with_parents:
        dcat_contact_key = ContactKey(organization_name, DCAT)
        if dcat_contact_key in contact_dict:
            continue
        organization_admin_userids = _get_organization_admin_userids(
            ogdremote,
            organization_name,
        )
        if (
            not organization_admin_userids
            and organization_with_parents[organization_name]
        ):
            organization_admin_userids = _get_organization_admin_userids(
                ogdremote,
                organization_with_parents[organization_name][0],
            )
        if organization_admin_userids:
            organization_admin_emails = _get_organization_admin_emails(
                ogdremote,
                organization_admin_userids,
            )
            contact_dict[dcat_contact_key] = organization_admin_emails
            continue
        contact_dict[dcat_contact_key] = [dcat_admin_email]
    for entry, value in contact_dict.items():
        log_and_echo_msg(f"{entry} is emailed to: {value}")
    return contact_dict


def _get_contacts_from_file(config):
    contact_file = get_config(config, "contacts", "csvfile", fallback=None)
    contact_dict = defaultdict(list)
    if contact_file:
        try:
            with open(contact_file, "r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if (
                        not row.get("organization_slug")
                        or not row.get("pkg_type")
                        or not row.get("contact_emails")
                    ):
                        continue
                    contact_key = ContactKey(
                        organization=row["organization_slug"], pkg_type=row["pkg_type"]
                    )
                    emails = row["contact_emails"].split(" ")
                    contact_dict[contact_key].extend(emails)
        except FileNotFoundError:
            raise click.UsageError(
                "'contacts.csv' file configured, but file was not found."
            )
        except AttributeError:
            raise click.UsageError(
                "'contacts.csv' file configured, but file has " "not the correct format"
            )
    return contact_dict


def get_pkg_metadata_contacts(send_to, contact_points):
    if send_to:
        return [Contact(email, email) for email in send_to]
    return get_pkg_contacts(contact_points)


def log_and_echo_msg(msg, error=False):
    if error:
        log.error(msg)
    else:
        log.info(msg)
    click.echo(f"{msg}")


def get_pkg_dcat_serialization_url(siteurl, name):
    return siteurl + "/dataset/" + name + ".rdf"


def get_harvest_source_url(pkg, dcat_harvesters):
    harvester_source_id = [
        item["value"]
        for item in pkg.get("extras", [])
        if item["key"] == "harvest_source_id"
    ]
    if not harvester_source_id:
        return None
    harvest_source_url = dcat_harvesters.get(harvester_source_id[0])
    if not harvest_source_url:
        return None
    return harvest_source_url


def set_runparms(org, limit, pkg, run, configpath, build, send, mode, test):
    config = configparser.ConfigParser()
    config.read(configpath)
    if not config.sections():
        raise click.UsageError(
            f"Configuration could not be read from file '{configpath}'. Make"
            f"sure that the fill exists and contains a configuration such as provided"
            f"in 'config.ini.dist'"
        )
    nr_scope_options = len([opt for opt in [limit, pkg, org] if opt])
    if len([opt for opt in [limit, pkg, org] if opt]) > 1:
        raise click.UsageError(
            "Only one of the options --org, --limit, " "--pkg can be used."
        )
    check = False
    if run:
        if nr_scope_options or mode:
            raise click.UsageError(
                "--rundir can only be used with "
                "--build and --send:\n"
                "it implies that the check has "
                "already been performed "
                "and just the emails\n"
                "should be build and send out"
            )
    else:
        if mode and mode not in [MODE_SHACL, MODE_LINK]:
            raise click.UsageError(
                f"--mode can only contain {MODE_SHACL} or {MODE_LINK}"
            )

    tmpdir = Path(get_config(config, "tmpdir", "tmppath", required=True))
    siteurl = get_config(config, "site", "siteurl", required=True)
    envpath = get_config(config, "env", "envpath", required=True)
    load_dotenv(dotenv_path=envpath)
    apikey = os.environ.get("CKAN_API_KEY")
    if run:
        mode = _get_mode_from_runname(run)
        check = False
        rundir = tmpdir / run
    else:
        check = True
        run = _get_runname(org=org, limit=limit, pkg=pkg, mode=mode)
        rundir = _make_dirs(tmpdir=tmpdir, runname=run)
    runparms = RunParms(
        siteurl=siteurl,
        org=org,
        pkg=pkg,
        limit=limit,
        config=config,
        apikey=apikey,
        tmpdir=tmpdir,
        rundir=rundir,
        mode=mode,
        check=check,
        build=build,
        send=send,
        test=test,
    )
    logdir = get_logdir(rundir)
    loglevel = get_config(config, "logging", "level", fallback="INFO")
    _setup_loggers(logdir, loglevel)
    _log_run_parms(runparms)
    return runparms


def _log_run_parms(runparms):
    info = "Run of pkg_checker:\n-------------------\n"
    for name, value in runparms._asdict().items():
        if name == "config":
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
        filename=logdir / "package-checker.log",
        format="%(asctime)s %(levelname)s %(message)s",
        level=loglevel,
        filemode="a+",
    )


def _make_dirs(tmpdir, runname):
    rundir = tmpdir / runname
    try:
        rundir.mkdir()
    except Exception as e:
        click.echo(
            f"An Error {e} occured:\n"
            f"The specified tmp directory {rundir} does not exist.\n"
            f"Please set it up and run again."
        )
        sys.exit()
    maildir = get_maildir(rundir)
    maildir.mkdir()
    logdir = get_logdir(rundir)
    logdir.mkdir()
    csvdir = get_csvdir(rundir)
    csvdir.mkdir()
    return rundir


def _get_runname(org, pkg, mode, limit):
    name_parts = []
    name_parts.append(datetime.now().strftime("%Y-%m-%d-%H%M"))
    if mode:
        name_parts.append(f"{mode}")
    if org:
        name_parts.append(f"org-{org[:10]}")
    if pkg:
        name_parts.append(f"pkg-{pkg[:10]}")
    if limit:
        name_parts.append(f"limit-{limit}")
    runname = "-".join(name_parts)
    return runname


def _get_mode_from_runname(runname):
    mode = [part for part in runname.split("-") if part in modes]
    if mode:
        return mode[0]
    else:
        raise click.UsageError(f"Mode can not be detected from {runname}.")


def contacts_statistics(
    checker_result_path, checker_error_fieldname, contactsstats_filename
):
    df = pd.read_csv(checker_result_path)
    dg_contacts = df.filter(["contact_email", "pkg_type", "organization_name"])\
                    .groupby(["organization_name", "pkg_type"]).apply(
                        _list_contact_emails
                    )
    dg_contacts.name = "contacts"
    dg_errors = df.filter([checker_error_fieldname, "pkg_type", "organization_name"])\
                  .groupby(["organization_name", "pkg_type"]).count()
    df_result = dg_errors.join(dg_contacts)
    statfile = open(contactsstats_filename, "w")
    statwriter = csv.DictWriter(
        statfile,
        fieldnames=["organization_name", "pkg_type", "error_count", "contact_emails"],
    )
    statwriter.writeheader()
    for index, row in df_result.iterrows():
        statwriter.writerow(
            {
                "organization_name": index[0],
                "pkg_type": index[1],
                "error_count": row[checker_error_fieldname],
                "contact_emails": row["contacts"],
            }
        )


def _list_contact_emails(df):
    contacts = df["contact_email"].to_list()
    contacts_unique = list(set(contacts))
    contacts_unique_formatted = " ".join(contacts_unique)
    return contacts_unique_formatted
