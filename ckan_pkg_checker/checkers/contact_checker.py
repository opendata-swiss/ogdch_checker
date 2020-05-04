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
        self.geocat_contact = utils.Contact(
            name=config.get('contactchecker', 'geocat_name'),
            email=config.get('contactchecker', 'geocat_email'))
        self.default_contact = utils.Contact(
            name=config.get('contactchecker', 'default_name'),
            email=config.get('contactchecker', 'default_email'))
        self.contact_cache = {}
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
                if recipient not in self.contact_cache.keys():
                    if pkg['name'] in self.geocat_pkg_ids:
                        send_to = self.geocat_contact
                    else:
                        send_to = recipient
                    log.info("CONTACTCHECKER: ENTRY: Recipient: {} Send to: {}"
                             .format(recipient, send_to))
                    self.write_result(recipient, send_to)
                    self.contact_cache[recipient] = send_to

    def write_result(self, recipient, send_to):
        """Check one data package"""
        self.writer.writerow(
            {
                'contact_email': recipient.email,
                'contact_name': recipient.name,
                'send_to_email': send_to.email,
                'send_to_name': send_to.name,
            }
        )
        click.echo("Contact added for: recipient {} sent_to {}".format(
            recipient.email, send_to.email
        ))

    def finish(self):
        """close output file"""
        self.outfile.close()
