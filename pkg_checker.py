"""
Script to start the Worklogdb Application
"""
import logging

import click

from ckan_pkg_checker.email_builder import EmailBuilder
from ckan_pkg_checker.email_sender import EmailSender
from ckan_pkg_checker.pkg_checker import PackageCheck
from ckan_pkg_checker.utils.utils import MODE_SHACL, set_runparms

log = logging.getLogger(__name__)


@click.command()
@click.option(
    "-l",
    "--limit",
    type=int,
    help="Limit the number of packages to check. Example: --limit 20.",
)
@click.option(
    "-p",
    "--pkg",
    help="Check only a single package. Example: --pkg vbz-haltestellen.",
)
@click.option(
    "-o", "--org", help="Check only a single organization. Example --org bernmobil."
)
@click.option(
    "-m",
    "--mode",
    default=None,
    help="Mode: LinkChecker (link) or ShaclChecker (shacl). Example --m link.",
)
@click.option(
    "-c",
    "--configpath",
    help="Path to the configuration file. "
    "Example --config config/development.ini"
    "The checker must always be run with a "
    "configuration file.",
)
@click.option(
    "-b",
    "--build/--no-build",
    default=False,
    help="Build the mails in the mails directory. "
    "Example --build."
    "By default the build is not performed.",
)
@click.option(
    "-s",
    "--send/--no-send",
    default=False,
    help="Send the emails from the mail directory. "
    "Example: --send."
    "By default the mails are not send.",
)
@click.option(
    "-t",
    "--test/--no-test",
    default=False,
    help="Tests the sending of emails by logging instead of sending" "Example: --test.",
)
@click.option(
    "-r",
    "--run",
    help="Run directory name to use for the build "
    "and send of mails. "
    "Example --run 2022-11-28-2104-shacl. "
    "This assumes the checker has run before and has "
    "set up a directory with results "
    "of that run. With this option mails can be build and "
    "send out from the results of a previous checker run.",
)
def check_packages(
    limit=None,
    pkg=None,
    org=None,
    configpath=None,
    build=False,
    send=False,
    run=None,
    test=False,
    mode=MODE_SHACL,
):
    """Checks data packages of a opendata.swiss
    ---------------------------------------

    It must always be called with --configpath

    You can limit the scope of the packages checked by --limit,
    --pkg or --org

    Only when you call it with --build and --send email messages
    will be sent out

    For datasets harvested by geocat a geocat email can be
    specified in the configuration file.

    You can just send emails when you run the command with --run and --send.
    This assumes a previous check run has been taken place.
    """
    runparms = set_runparms(
        org=org,
        limit=limit,
        pkg=pkg,
        run=run,
        configpath=configpath,
        build=build,
        send=send,
        test=test,
        mode=mode,
    )

    if runparms.check:
        check = PackageCheck(
            config=runparms.config,
            siteurl=runparms.siteurl,
            apikey=runparms.apikey,
            rundir=runparms.rundir,
            mode=runparms.mode,
            limit=runparms.limit,
            pkg=runparms.pkg,
            org=runparms.org,
        )
        check.run()
    if runparms.build:
        builder = EmailBuilder(
            rundir=runparms.rundir, mode=runparms.mode, config=runparms.config
        )
        builder.build()
    if runparms.send:
        sender = EmailSender(
            rundir=runparms.rundir,
            config=runparms.config,
            test=runparms.test,
            mode=runparms.mode,
        )
        sender.send()


if __name__ == "__main__":
    check_packages()
