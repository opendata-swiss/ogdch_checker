import csv
import logging
from collections import namedtuple
from ckan_pkg_checker.utils import utils
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
PublisherInfo = namedtuple('PublisherInfo', ['organization', 'publisher'])

log = logging.getLogger(__name__)


class PublisherChecker(CheckerInterface):
    def __init__(self, rundir, config, siteurl):
        """Initialize the validation checker"""
        self.siteurl = siteurl
        csvfile = utils.get_csvdir(rundir) / utils.get_config(config, 'publisherchecker', 'csvfile', required=True)
        self._prepare_csv_file(csvfile)
        self.publisher_list = []

    def _prepare_csv_file(self, csvfile):
        self.csv_fieldnames = [
            'organization_slug',
            'publisher',
            'pkg_type',
        ]
        self.csvfile = open(csvfile, 'w')
        self.csvwriter = csv.DictWriter(
            self.csvfile, fieldnames=self.csv_fieldnames)
        self.csvwriter.writeheader()

    def check_package(self, pkg):
        """Check one data package"""
        organization = pkg.get('organization').get('name')
        publishers = pkg.get('publishers')
        if publishers:
            publisher = publishers[0].get('label')
            publisher_info = PublisherInfo(organization=organization, publisher=publisher)
            if not publisher_info in self.publisher_list:
                pkg_type = pkg.get('pkg_type', utils.DCAT)
                self.write_result(pkg, pkg_type, publisher_info)
                self.publisher_list.append(publisher_info)

    def write_result(self, pkg, pkg_type, publisher_info):
        organization = pkg.get('organization').get('name')
        self.csvwriter.writerow(
            {'organization_slug': publisher_info.organization,
             'publisher': publisher_info.publisher,
             'pkg_type': pkg_type,
             })

    def finish(self):
        """Close the file"""
        self.csvfile.close()

    def __repr__(self):
        return "Publisher Checker"
