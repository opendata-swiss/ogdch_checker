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
@click.option('-m', '--mode',
              help='Mode: LinkChecker (link) or ShaclChecker (shacl) . '
                   'Example --m link. Default is ShaclChecker')
@click.option('-c', '--configpath',
              help='Path to the configuration file. '
                   'Example --config config/development.ini'
                   'The checker must always be run with a '
                   'configuration file.')
@click.option('-u', '--siteurl',
              help='Siteurl: the url of the site where datasets are validated. '
                   'Example --siteurl https://opendata.swiss'
                   'the fallback ist the siteurl specified in the '
                   'configuration file.')
@click.option('-b', '--build/--no-build', default=False,
              help='Build the mails in the mails directory. '
                   'Example --build.'
                   'By default the build is not performed.')
@click.option('-s', '--send/--no-send', default=False,
              help='Send the emails from the mail directory. '
                   'Example: --send.'
                   'By default the mails are not send.')
@click.option('-t', '--test/--no-test', default=False,
              help='Tests the sending of emails by logging instead of sending'
                   'Example: --test.')
@click.option('-r', '--run',
              help='Run directory name to use for the build '
                   'and send of mails. '
                   'Example --run tmpxchgfrti.'
                   'This assumes the checker has run before and has '
                   'set up a directory with results '
                   'of that run. With this option mails can be build and '
                   'send out from the results of a previous checker run.')
def check_packages(limit=None, pkg=None, org=None, configpath=None, siteurl=None,
                   build=False, send=False, run=None, test=False, mode=utils.MODE_SHACL):
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
    config = configparser.ConfigParser()
    config.read(configpath)
    if not config.sections():
        raise click.UsageError(f"Configuration could not be read from file '{configpath}'")
    tmpdir = Path(utils._get_config(config, 'tmpdir', 'tmppath'))
    if not siteurl:
        siteurl = utils._get_config(config, 'site', 'siteurl')
    try:
        runparms = _check_and_format_runparms(
            org=org,
            limit=limit,
            pkg=pkg,
            run=run,
            mode=mode,
            siteurl=siteurl,
            configpath=configpath,
            build=build,
            send=send)
    except click.UsageError as e:
        raise(e)

    if not run:
        run_checkers = True
        runname = utils._get_runname()
        rundir = utils._make_dirs(tmpdir=tmpdir, rundir=runname)
        build_mails = build or send or test
    else:
        run_checkers = False
        rundir = tmpdir / run
        build_mails = build

    runparms += "Find output at {}".format(rundir)

    logdir = utils._get_logdir(rundir)
    loglevel = utils._get_config(config, 'logging', 'level')
    utils._setup_loggers(logdir, loglevel)

    if run_checkers:
        click.echo(runparms)
        check = PackageCheck(
            config=config,
            siteurl=siteurl,
            limit=limit,
            mode=mode,
            pkg=pkg,
            org=org,
            rundir=rundir,
        )
        check.run()
    if build or send or test:
        sender = EmailSender(
            rundir=rundir,
            config=config,
            test=test,
            mode=mode,
        )
        if build_mails:
            click.echo("building emails")
            sender.build()
        if send or test:
            click.echo("sending emails")
            sender.send()


def _check_and_format_runparms(
        org, limit, pkg, run, configpath, siteurl, build, send, mode):
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
    if mode and mode not in [utils.MODE_SHACL, utils.MODE_LINK]:
        raise click.UsageError(f"--mode can only contain {utils.MODE_SHACL} or {utils.MODE_LINK}")
    if siteurl and siteurl not in [utils.SITE_ABNAHME, utils.SITE_TEST, utils.SITE_PROD]:
        raise click.UsageError("--siteurl can only contain the following urls:\n"
                               f"{utils.SITE_PROD}\n{utils.SITE_ABNAHME}\n{utils.SITE_TEST}")
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
    if mode:
        runparms += "mode        : {}\n".format(mode)
    if siteurl:
        runparms += "siteurl     : {}\n".format(siteurl)
    return runparms


if __name__ == '__main__':
    check_packages()
