"""
Script to start the Worklogdb Application
"""
import click
import configparser
import logging
from pathlib import Path

from ckan_pkg_checker.pkg_checker import PackageCheck
from ckan_pkg_checker.email_sender import EmailSender
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


@click.command()
@click.option('-l', '--limit', type=int,
              help='Limit the number of packages to check. '
                   'Example: --limit 20.')
@click.option('-p', '--pkg',
              help='Check only a single package. '
                   'Example: --pkg vbz-haltestellen.')
@click.option('-o', '--org',
              help='Check only a single organization. '
                   'Example --org bernmobil.')
@click.option('-c', '--configpath',
              help='Path to the configuration file. '
                   'Example --config config/development.ini'
                   'The checker must always be run with a '
                   'configuration file.')
@click.option('-b', '--build/--no-build', default=False,
              help='Build the mails in the mails directory. '
                   'Example --build.'
                   'By default the build is not performed.')
@click.option('-s', '--send/--no-send', default=False,
              help='Send the emails from the mail directory. '
                   'Example: --send.'
                   'By default the mails are not send.')
@click.option('-r', '--run',
              help='Run directory name to use for the build '
                   'and send of mails. '
                   'Example --run tmpxchgfrti.'
                   'This assumes the checker has run before and has '
                   'set up a directory with results '
                   'of that run. With this option mails can be build and '
                   'send out from the results of a previous checker run.')
def check_packages(limit=None, pkg=None, org=None, configpath=None,
                   build=False, send=False, run=None):
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
    try:
        runparms = _check_and_format_runparms(
            org=org,
            limit=limit,
            pkg=pkg,
            run=run,
            configpath=configpath,
            build=build,
            send=send)
    except click.UsageError as e:
        raise(e)

    config = configparser.ConfigParser()
    try:
        config.read(configpath)
        tmpdir = Path(config.get('tmpdir', 'tmppath'))
    except configparser.Error as e:
        raise click.UsageError(
            "Configuration Error {} in configuration file '{}'"
            .format(e, configpath))

    if not run:
        run_checkers = True
        runname = utils._get_runname()
        rundir = utils._make_dirs(tmpdir=tmpdir, rundir=runname)
    else:
        run_checkers = False
        rundir = tmpdir / run

    runparms += "Find output at {}".format(rundir)

    logging.basicConfig(
        filename=utils._get_logdir(rundir) / 'package-checker.log',
        format='%(asctime)s %(levelname)s %(name)s %(message)s %(funcName)s %(lineno)d', # noqa
        level=config.get('logging', 'level'),
        filemode='a+'
    )

    if run_checkers:
        click.echo(runparms)
        check = PackageCheck(
            configpath=configpath,
            limit=limit,
            pkg=pkg,
            org=org,
            rundir=rundir,
        )
        check.run()

    if build or send:
        sender = EmailSender(
            rundir=rundir,
            configpath=configpath
        )
        click.echo("building emails")
        sender.build()
        if send:
            click.echo("sending emails")
            sender.build()
            sender.send()


def _check_and_format_runparms(
        org, limit, pkg, run, configpath, build, send):
    nr_scope_options = \
        len([opt for opt in [limit, pkg, org] if opt])
    if not configpath:
        raise click.UsageError("The package checker needs a "
                               "configuration path\n"
                               "--config must always be used.")
    if len([opt for opt in [limit, pkg, org] if opt]) > 1:
        raise click.UsageError("Only one of the options --org, --limit, "
                               "--pkg can be used.")
    if run and nr_scope_options:
        raise click.UsageError("--rundir can only be used with "
                               "--build and --send:\n"
                               "it implies that the check has "
                               "already been performed "
                               "and just the emails\n"
                               "should be build and send out")
    runparms = "Run of pkg_checker:\n-------------------\n"
    if org:
        runparms += "organization: {}\n".format(org)
    if limit:
        runparms += "limit       : {}\n".format(limit)
    if pkg:
        runparms += "package     : {}\n".format(pkg)
    if configpath:
        runparms += "configpath  : {}\n".format(configpath)
    if run:
        runparms += "run         : {}\n".format(run)
    if build:
        runparms += "build mails : {}\n".format(build)
    if send:
        runparms += "send mails  : {}\n".format(send)
    return runparms


if __name__ == '__main__':
    check_packages()
