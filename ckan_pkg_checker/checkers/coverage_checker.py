import csv
import click
import logging
from configparser import ConfigParser

from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)

class CoverageChecker(CheckerInterface):
    def initialize(self, rundir, configpath):
        """Initialize the contact checker"""
        config = ConfigParser()
        config.read(configpath)
        csvfile = utils._get_csvdir(rundir) / config.get(
            'coveragechecker', 'csvfile')
        self._prepare_csv_file(csvfile)

    def _prepare_csv_file(self, csvfile):
        self.outfile = open(csvfile, 'w')
        self.writer = csv.DictWriter(
            self.outfile, fieldnames=['dataset','resource','coverage'])
        self.writer.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        for resource in pkg['resources']:
            if resource.get('coverage'):
                self.write_result(pkg, resource)

    def write_result(self, pkg, resource):
        """Check one data package"""
        self.writer.writerow(
            {
                'dataset': pkg.get('name'),
                'resource': resource.get('id'),
                'coverage': resource.get('coverage'),
            }
        )
        click.echo("coverage added {}: {}".format(pkg.get('name'),
            resource.get('coverage')
        ))

    def finish(self):
        """close output file"""
        self.outfile.close()
