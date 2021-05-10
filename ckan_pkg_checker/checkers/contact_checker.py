import csv
import click
import logging
from collections import namedtuple
from configparser import ConfigParser

from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)

CheckResult = namedtuple('ContactResult', ['pkg_id', 'contact', ])


class ContactChecker(CheckerInterface):
    def initialize(self, geocat_packages, rundir, configpath):
        """Initialize the contact checker"""
        self.geocat_pkg_ids = geocat_packages
        config = ConfigParser()
        config.read(configpath)
        csvfile = utils._get_csvdir(rundir) / config.get(
            'contactchecker', 'csvfile')
        self.default_contact = utils.Contact(
            name=config.get('emailsender', 'default_name'),
            email=config.get('emailsender', 'default_email'))
        self._prepare_csv_file(csvfile)

    def _prepare_csv_file(self, csvfile):
        self.outfile = open(csvfile, 'w')
        self.writer = csv.DictWriter(
            self.outfile, fieldnames=utils.FieldNamesContactFile)
        self.writer.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        if pkg.get('contact_points', ''):
            recipients = utils.get_pkg_contacts(pkg.get('contact_points'))
            for recipient in recipients:
                if pkg['name'] in self.geocat_pkg_ids:
                    pkg_type = utils.GEOCAT
                else:
                    pkg_type = utils.DCAT
                self.write_result(recipient, pkg['name'], pkg_type)

    def write_result(self, recipient, dataset, pkg_type):
        """Check one data package"""
        self.writer.writerow(
            {
                'contact_email': recipient.email,
                'contact_name': recipient.name,
                'dataset': dataset,
                'pkg_type': pkg_type,
            }
        )

    def finish(self):
        """close output file"""
        self.outfile.close()
