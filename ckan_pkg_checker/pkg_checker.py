import logging

import ckanapi
import click

from ckan_pkg_checker.checkers.link_checker import LinkChecker
from ckan_pkg_checker.checkers.shacl_checker import ShaclChecker
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)
DCAT_HARVESTER_TYPES = {"dcat_ch_rdf", "dcat_ch_i14y_rdf"}


class PackageCheck:
    def __init__(self, config, siteurl, apikey, rundir, mode, limit, pkg, org):
        self.siteurl = siteurl
        self.ogdremote = ckanapi.RemoteCKAN(self.siteurl, apikey=apikey)
        self.dcat_harvesters = self._get_dcat_harvester_dict()
        self.pkgs = self._get_packages(limit=limit, pkg=pkg, org=org)
        self.pkgs_count = len(self.pkgs)
        self.geocat_pkg_ids = self._get_geocat_package_ids()
        self.contact_dict = utils.set_up_contact_mapping(config, self.ogdremote)
        self.active_checkers = []
        checker_classes = []
        kwargs = {"rundir": rundir, "config": config, "siteurl": siteurl}
        if mode == utils.MODE_SHACL:
            checker_classes.append(ShaclChecker)
        elif mode == utils.MODE_LINK:
            checker_classes.append(LinkChecker)
        for checker_class in checker_classes:
            checker = checker_class(**kwargs)
            self.active_checkers.append(checker)
        utils.log_and_echo_msg(f"--> {self.pkgs_count} datasets to process")

    def run(self):
        for idx, id in enumerate(self.pkgs):
            utils.log_and_echo_msg(f"({idx + 1}/{self.pkgs_count}) DATASET {id}")
            try:
                result = self.ogdremote.action.package_search(
                    fq=f"name:({id})", include_private=True
                )
                if not result.get("results"):
                    utils.log_and_echo_msg(f"No dataset found for id: {id}")
                    continue
                pkg = result.get("results")[0]
                self._enrich_package(pkg)
                if pkg["type"] == "dataset":
                    for checker in self.active_checkers:
                        checker.check_package(pkg)
            except ckanapi.errors.NotFound:
                utils.log_and_echo_msg(f"No dataset found for id: {id}")
            except ckanapi.errors.CKANAPIError:
                utils.log_and_echo_msg(f"CKAN Api Error for Dataset: {id}")
        for checker in self.active_checkers:
            checker.finish()

    def _enrich_package(self, pkg):
        if pkg["name"] in self.geocat_pkg_ids:
            pkg["pkg_type"] = utils.GEOCAT
        else:
            pkg["pkg_type"] = utils.DCAT
        pkg["source_url"] = utils.get_harvest_source_url(pkg, self.dcat_harvesters)
        if pkg.get("organization"):
            org_slug = pkg["organization"].get("name")  # this is the slug in CKAN
            contact_key = utils.ContactKey(
                organization=org_slug, pkg_type=pkg["pkg_type"]
            )
            if contact_key in self.contact_dict:
                pkg["send_to"] = self.contact_dict.get(contact_key)

            utils.log_and_echo_msg(
                f"Using org_slug: {org_slug}, pkg_type: {pkg['pkg_type']}"
            )

    def _get_packages(self, limit=None, pkg=None, org=None):
        if pkg:
            return [pkg]
        elif org:
            return self._get_organization_package_ids(org=org)
        else:
            return self._get_all_package_ids(limit)

    def _get_dcat_harvester_dict(self):
        try:
            harvesters = self.ogdremote.action.harvest_source_list()
            harvester_dict = {}
            for harvester in harvesters:
                if harvester.get("type") in DCAT_HARVESTER_TYPES:
                    harvester_dict[harvester["id"]] = harvester.get("url")
            return harvester_dict
        except Exception as e:
            log.exception(f"getting harvesters failed: {e}")

    def _get_all_package_ids(self, limit=None):
        pkg_ids = []
        try:
            pkg_ids = self.ogdremote.action.package_list()
        except Exception as e:
            log.exception(f"getting packages failed: {e}")
        public_packages = [id for id in pkg_ids if not id.startswith("__")]
        if limit:
            return public_packages[:limit]
        return public_packages

    def _get_organization_package_ids(self, org):
        fq_organization = f"organization:{org}"
        organization_pkg_ids = self._get_pkg_ids_from_package_search(fq_organization)
        return organization_pkg_ids

    def _get_geocat_package_ids(self):
        fq_geocat_harvesters = "dataset_type:harvest AND source_type:geocat_harvester"
        geocat_harvester_ids = self._get_pkg_ids_from_package_search(
            fq=fq_geocat_harvesters, target="id"
        )
        utils.log_and_echo_msg(
            f"Found geocat harvester IDs: {geocat_harvester_ids}")
        fq_geocat_pkgs = "harvest_source_id:(" + " OR ".join(geocat_harvester_ids) + ")"
        geocat_pkg_ids = self._get_pkg_ids_from_package_search(fq_geocat_pkgs)
        return geocat_pkg_ids

    def _get_pkg_ids_from_package_search(self, fq, target="name"):
        rows = 500
        page = 0
        pkg_ids = []
        result_count = 0
        while page == 0 or len(pkg_ids) < result_count:
            try:
                page = page + 1
                start = (page - 1) * rows
                result = self.ogdremote.action.package_search(
                    fq=fq, rows=rows, start=start,
                    **{"fl": "id name extras"} # Force extras to be returned if possible
                )
                if not result_count:
                    result_count = result["count"]
                pkg_ids.extend([pkg[target] for pkg in result["results"]])
            except ckanapi.errors.NotFound:
                utils.log_and_echo_msg(f"No datasets found for search with fq: {fq}")
            except ckanapi.errors.CKANAPIError:
                utils.log_and_echo_msg(f"CKAN Api Error for Dataset Search: {fq} ({e})")
        return pkg_ids
