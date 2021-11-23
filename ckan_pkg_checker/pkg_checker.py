import ckanapi
import logging
import click
from ckanapi.errors import NotFound as DatasetNotFoundException
from ckan_pkg_checker.checkers.link_checker import LinkChecker
from ckan_pkg_checker.checkers.shacl_checker import ShaclChecker
from ckan_pkg_checker.checkers.publisher_checker import PublisherChecker
from ckan_pkg_checker.utils.utils import (log_and_echo_msg, MODE_SHACL, MODE_LINK, MODE_PUBLISHER,
                                          set_up_contact_mapping, DCAT, GEOCAT, ContactKey)

log = logging.getLogger(__name__)


class PackageCheck():
    def __init__(self, config, siteurl, rundir, mode, limit, pkg, org):
        self.siteurl = siteurl
        self.ogdremote = ckanapi.RemoteCKAN(self.siteurl)
        self.pkgs = self._get_packages(
            limit=limit, pkg=pkg, org=org)
        self.pkgs_count = len(self.pkgs)
        self.geocat_pkg_ids = self._get_geocat_package_ids()
        self.contact_dict = set_up_contact_mapping(config)
        self.active_checkers = []
        checker_classes = []
        kwargs = {'rundir': rundir, 'config': config, 'siteurl': siteurl}
        if mode == MODE_SHACL:
            checker_classes.append(ShaclChecker)
        elif mode == MODE_LINK:
            checker_classes.append(LinkChecker)
        elif mode == MODE_PUBLISHER:
            checker_classes.append(PublisherChecker)
        for checker_class in checker_classes:
            checker = checker_class(**kwargs)
            self.active_checkers.append(checker)
        log_and_echo_msg(f"--> {self.pkgs_count} datasets to process")

    def run(self):
        for idx, id in enumerate(self.pkgs):
            log_and_echo_msg(f"({idx + 1}/{self.pkgs_count}) DATASET {id}")
            try:
                pkg = self.ogdremote.action.package_show(id=id)
                self._enrich_package(pkg)
                if pkg['type'] == 'dataset':
                    for checker in self.active_checkers:
                        checker.check_package(pkg)
            except DatasetNotFoundException:
                log_and_echo_msg(f"No dataset found for id: {id}")
        for checker in self.active_checkers:
            checker.finish()

    def _enrich_package(self, pkg):
        if pkg['name'] in self.geocat_pkg_ids:
            pkg['pkg_type'] = GEOCAT
        else:
            pkg['pkg_type'] = DCAT
        if pkg.get('organization'):
            contact_key = ContactKey(organization=pkg['organization'].get('name'),
                                     pkg_type=pkg['pkg_type'])
            if contact_key in self.contact_dict:
                email = self.contact_dict.get(contact_key)
                pkg['send_to'] = email
                click.echo(email)

    def _get_packages(self, limit=None, pkg=None, org=None):
        if pkg:
            return [pkg]
        elif org:
            return self._get_organization_package_ids(org=org)
        else:
            return self._get_all_package_ids(limit)

    def _get_all_package_ids(self, limit=None):
        pkg_ids = []
        try:
            pkg_ids = self.ogdremote.action.package_list()
        except Exception as e:
            log.exception(f"getting packages failed: {e}")
        public_packages = [id for id in pkg_ids if not id.startswith('__')]
        if limit:
            return public_packages[:limit]
        return public_packages

    def _get_organization_package_ids(self, org):
        fq_organization = f"organization:{org}"
        organization_pkg_ids = \
            self._get_pkg_ids_from_package_search(fq_organization)
        return organization_pkg_ids

    def _get_geocat_package_ids(self):
        fq_geocat_harvesters = \
            'dataset_type:harvest AND source_type:geocat_harvester'
        geocat_harvester_ids = \
            self._get_pkg_ids_from_package_search(fq=fq_geocat_harvesters, target='id')
        fq_geocat_pkgs = \
            'harvest_source_id:(' + ' OR '.join(geocat_harvester_ids) + ')'
        geocat_pkg_ids = \
            self._get_pkg_ids_from_package_search(fq_geocat_pkgs)
        return geocat_pkg_ids

    def _get_pkg_ids_from_package_search(self, fq, target='name'):
        rows = 500
        page = 0
        pkg_ids = []
        result_count = 0
        while page == 0 or len(pkg_ids) < result_count:
            try:
                page = page + 1
                start = (page - 1) * rows
                result = self.ogdremote.action.package_search(
                    fq=fq, rows=rows, start=start)
                if not result_count:
                    result_count = result['count']
                pkg_ids.extend([pkg[target] for pkg in result['results']])
            except DatasetNotFoundException:
                log_and_echo_msg(f"No datasets found for search with fw: {fq}")
        return pkg_ids
