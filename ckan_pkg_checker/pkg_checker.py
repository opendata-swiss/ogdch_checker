import ckanapi
from configparser import ConfigParser
from ckan_pkg_checker.checkers.contact_checker import ContactChecker
from ckan_pkg_checker.checkers.checker_interface import CheckerInterface
# this import in needed because the LinkChecker Class is used here
from ckan_pkg_checker.checkers.link_checker import LinkChecker # noqa

import logging
log = logging.getLogger(__name__)


class PackageCheck():
    def __init__(self, limit, pkg, org, rundir, configpath):
        config = ConfigParser()
        config.read(configpath)
        self.siteurl = config.get('site', 'siteurl')
        self.ogdremote = ckanapi.RemoteCKAN(self.siteurl)
        self.pkgs = self._get_packages(
            limit=limit, pkg=pkg, org=org)
        self.pkgs_count = len(self.pkgs)
        self.active_checkers = []
        checker_classnames = config.get(
            'checkers', 'checker_classnames').split(' ')
        for checker_class in _get_checker_classes(
                checker_names=checker_classnames):
            checker = checker_class()
            kwargs = {'rundir': rundir, 'configpath': configpath}
            if checker_class in [ContactChecker, LinkChecker]:
                geocat_pkg_ids = self._get_geocat_package_ids()
                kwargs['geocat_packages'] = geocat_pkg_ids
            checker.initialize(**kwargs)
            self.active_checkers.append(checker)
        log.info(
            "CHECKER-CONFIG:\nsiteurl: {}\nlimit: {}\npackages: {}"
            "\norganizations: {}\ncheckers: {}"
            .format(self.siteurl, limit, self.pkgs_count, org,
                    self.active_checkers))

    def run(self):
        for idx, id in enumerate(self.pkgs):
            log.info("({}/{}) DATASET {}".format(idx + 1, self.pkgs_count, id))
            try:
                pkg = self.ogdremote.action.package_show(id=id)
                if pkg['type'] == 'dataset':
                    for checker in self.active_checkers:
                        checker.check_package(pkg)
            except Exception as e:
                log.exception('check_package failed {}'.format(e))
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
            except Exception as e:
                log.exception("Error occured while searching for packages "
                              "with fq: {}, error: {}"
                              .format(fq, e))
        return pkg_ids


def _get_checker_classes(checker_names):
    checkerclasses = []
    for checkername in checker_names:
        try:
            checker = eval(checkername)
            assert(issubclass(checker, CheckerInterface))
        except Exception as e:
            raise(e)
        else:
            checkerclasses.append(checker)
    return checkerclasses
