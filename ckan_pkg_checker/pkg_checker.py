import ckanapi
from configparser import ConfigParser
from ckanapi.errors import NotFound as DatasetNotFoundException
from ckan_pkg_checker.checkers.link_checker import LinkChecker
from ckan_pkg_checker.checkers.shacl_checker import ShaclChecker
from ckan_pkg_checker.utils import utils

import logging
log = logging.getLogger(__name__)


class PackageCheck():
    def __init__(self, limit, pkg, org, rundir, config, siteurl, mode):
        self.siteurl = siteurl
        self.ogdremote = ckanapi.RemoteCKAN(self.siteurl)
        self.pkgs = self._get_packages(
            limit=limit, pkg=pkg, org=org)
        self.pkgs_count = len(self.pkgs)
        self.geocat_pkg_ids = self._get_geocat_package_ids()
        self.active_checkers = []
        checker_classes = []
        kwargs = {'rundir': rundir, 'config': config, 'siteurl': siteurl}
        if mode == utils.MODE_SHACL:
            checker_classes.append(ShaclChecker)
        elif mode == utils.MODE_LINK:
            checker_classes.append(LinkChecker)
        for checker_class in checker_classes:
            checker = checker_class()
            checker.initialize(**kwargs)
            self.active_checkers.append(checker)
        run_info = utils._get_run_info(org, pkg, limit)
        log.info(
            f"Run of ogdch_checker:\nsiteurl: {self.siteurl}\nrun info: {run_info}"
            f"\nmode: {mode}\n--> {self.pkgs_count} datasets to process")

    def run(self):
        for idx, id in enumerate(self.pkgs):
            log.info("({}/{}) DATASET {}".format(idx + 1, self.pkgs_count, id))
            try:
                pkg = self.ogdremote.action.package_show(id=id)
                if pkg['name'] in self.geocat_pkg_ids :
                    pkg['pkg_type'] = utils.GEOCAT
                else:
                    pkg['pkg_type'] = utils.DCAT
                if pkg['type'] == 'dataset':
                    for checker in self.active_checkers:
                        checker.check_package(pkg)
            except DatasetNotFoundException as e:
                log.error(f"No dataset found for id: {id}")
        for checker in self.active_checkers:
            checker.finish()

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
            log.exception('getting packages failed: {}'.format(e))
        public_packages = [id for id in pkg_ids if not id.startswith('__')]
        if limit:
            return public_packages[:limit]
        return public_packages

    def _get_organization_package_ids(self, org):
        fq_organization = 'organization:{}'.format(org)
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
            except DatasetNotFoundException as e:
                log.error(f"No datasets found for search with fw: {fq}")
        return pkg_ids
