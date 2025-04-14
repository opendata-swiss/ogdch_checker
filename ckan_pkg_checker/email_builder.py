import csv
import logging
import os

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailBuilder:
    def __init__(self, rundir, mode, config):
        self.mode = mode
        self.mailpath = utils.get_maildir(rundir)
        runpath = utils.get_csvdir(rundir)
        if mode == utils.MODE_SHACL:
            self.csvpath = runpath / utils.get_config(
                config, "shaclchecker", "csvfile", required=True
            )
            self.statpath = runpath / utils.get_config(
                config, "shaclchecker", "statfile", required=True
            )
        elif mode == utils.MODE_LINK:
            self.csvpath = runpath / utils.get_config(
                config, "linkchecker", "csvfile", required=True
            )
            self.statpath = runpath / utils.get_config(
                config, "linkchecker", "statfile", required=True
            )
        self.contactsstats_path = runpath / utils.get_config(
            config, "contacts", "statsfile", required=True
        )
        self.default_contact = utils.Contact(
            name=utils.get_config(
                config, "emailbuilder", "default_name", required=True
            ),
            email=utils.get_config(
                config, "emailbuilder", "default_email", required=True
            ),
        )

    def build(self):
        utils.log_and_echo_msg("building emails")

        grouped = {}

        with open(self.csvpath, "r") as readfile:
            reader = csv.DictReader(readfile)
            for row in reader:
                contact_email = row["contact_email"]
                contact_name = row["contact_name"]
                pkg_type = row["pkg_type"]
                property_uri = row["property"]
                key = (contact_email, pkg_type)

                grouped.setdefault(key, {
                    "contact_name": contact_name,
                    "pkg_type": pkg_type,
                    "errors": {}
                })

                entry = grouped[key]

                error_group = entry["errors"].setdefault(property_uri, {
                    "severity": row["severity"],
                    "error_msg": row["error_msg"],
                    "datasets": []
                })

                error_group["datasets"].append({
                    "title": row["dataset_title"],
                    "url": row["dataset_url"]
                })

        for (email, pkg_type), data in grouped.items():
            self._write_grouped_email(email, data)

        if self.statpath:
            self._build_statistics()
        if self.contactsstats_path:
            self._build_contacts_statistics()

    def _write_grouped_email(self, contact_email, data):
        env = Environment(loader=FileSystemLoader("ckan_pkg_checker/email_templates"))
        template = env.get_template("grouped_shacl_error.html")

        context = {
            "receiver_name": data["contact_name"],
            "pkg_type": data["pkg_type"],
            "errors": data["errors"]
        }

        output = template.render(context=context)

        mailfile = os.path.join(self.mailpath, data["pkg_type"] + "#" + contact_email + ".html")
        with open(mailfile, "w") as f:
            f.write(output)

    def _build_statistics(self):
        filename = utils.STATISTICS + "#" + self.default_contact.email
        mailfile = os.path.join(self.mailpath, filename + ".html")
        utils.log_and_echo_msg(f"email for {filename}")
        with open(mailfile, "a") as writemail:
            df = pd.read_csv(self.statpath)
            df = df.set_index("message")
            statistics = df.to_dict()
            msg = utils.build_statistics_email(
                receiver_name=self.default_contact.name,
                mode=self.mode,
                statistics=statistics,
            )
            writemail.write(msg)

    def _build_contacts_statistics(self):
        filename = utils.CONTACTS_STATISTICS + "#" + self.default_contact.email
        mailfile = os.path.join(self.mailpath, filename + ".html")
        utils.log_and_echo_msg(f"email for {filename}")
        with open(mailfile, "a") as writemail:
            df = pd.read_csv(self.contactsstats_path)
            msg = utils.build_contacts_statistics_email(
                receiver_name=self.default_contact.name,
                mode=self.mode,
                df_statistics=df,
            )
            writemail.write(msg)
