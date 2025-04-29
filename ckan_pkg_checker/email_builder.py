import csv
import logging
import os
from collections import defaultdict

import pandas as pd

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
        utils.log_and_echo_msg("Building grouped validation emails")

        grouped_messages = defaultdict(lambda: defaultdict(list))
        
        # Read and group by contact -> (property, error) -> [rows]
        with open(self.csvpath, "r") as readfile:
            reader = csv.DictReader(readfile)
            for row in reader:
                contact_email = row["contact_email"]
                contact_name = row["contact_name"]
                key = (row["property"], row["error_msg"])
                grouped_messages[(contact_email, contact_name)][key].append(row)
                
        for (contact_email, contact_name), errors_dict in grouped_messages.items():
            self._write_grouped_email(contact_email, contact_name, errors_dict)
        
        if self.statpath:
            self._build_statistics()
        if self.contactsstats_path:
            self._build_contacts_statistics()

    def _write_grouped_email(self, contact_email, contact_name, grouped_errors):
        example_row = next(iter(next(iter(grouped_errors.values()))))  # get one row for meta info
        pkg_type = example_row["pkg_type"]
        mailfile = os.path.join(self.mailpath, f"{pkg_type}#{contact_email}.html")

        msg = utils.build_msg_per_contact(
            receiver_name=contact_name,
            checker_type=example_row["checker_type"],
            pkg_type=pkg_type,
        )

        for (property, error_msg), rows in grouped_errors.items():
            msg += f"<p><strong>Property:</strong> '{property}'</p>\n"
            msg += f"<p><strong>VIOLATION:</strong> {error_msg}</p>\n"
            msg += "<p><strong>Dataset(s):</strong><br>\n"
            for row in rows:
                msg += f"<a href='{row['dataset_url']}'>{row['dataset_title']}</a><br>\n"
            msg += "</p><br>\n"

        with open(mailfile, "w") as writemail:
            writemail.write(msg)
            
    # def _process_line(self, row):
    #     contacts = [utils.Contact(email=row["contact_email"], name=row["contact_name"])]
    #     if self.default_contact.email not in [contact.email for contact in contacts]:
    #         contacts.append(self.default_contact)
    #     for contact in contacts:
    #         pkg_type = row["pkg_type"]
    #         mailfile = os.path.join(
    #             self.mailpath, pkg_type + "#" + contact.email + ".html"
    #         )
    #         msg = ""
    #         if not os.path.isfile(mailfile):
    #             utils.log_and_echo_msg(
    #                 f"email for {row['pkg_type']}#{row['contact_email']}"
    #             )
    #             msg += utils.build_msg_per_contact(
    #                 receiver_name=contact.name,
    #                 checker_type=row["checker_type"],
    #                 pkg_type=row["pkg_type"],
    #             )
    #         msg += utils.build_msg_per_error(row)
    #         with open(mailfile, "a") as writemail:
    #             writemail.write(msg)

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
