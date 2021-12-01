import csv
import logging
import os
import pandas as pd

from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailBuilder:
    def __init__(self, rundir, mode, config):
        self.mode=mode
        self.mailpath = utils.get_maildir(rundir)
        runpath = utils.get_csvdir(rundir)
        if mode == utils.MODE_SHACL:
            csvfile = utils.get_config(config, "shaclchecker", "csvfile", required=True)
        elif mode == utils.MODE_LINK:
            csvfile = utils.get_config(config, "linkchecker", "csvfile", required=True)
        self.csvpath = runpath / csvfile
        statfile = utils.get_config(config, "shaclchecker", "statfile", required=False)
        self.statpath = runpath / statfile
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
        with open(self.csvpath, "r") as readfile:
            reader = csv.DictReader(readfile)
            for row in reader:
                self._process_line(row)
        self._build_statistics()

    def _process_line(self, row):
        contacts = [utils.Contact(email=row["contact_email"], name=row["contact_name"])]
        if self.default_contact.email not in [contact.email for contact in contacts]:
            contacts.append(self.default_contact)
        for contact in contacts:
            pkg_type = row["pkg_type"]
            mailfile = os.path.join(
                self.mailpath, pkg_type + "#" + contact.email + ".html"
            )
            msg = ""
            if not os.path.isfile(mailfile):
                utils.log_and_echo_msg(f"email for {row['pkg_type']}#{row['contact_email']}")
                msg += utils.build_msg_per_contact(
                    receiver_name=contact.name,
                    checker_type=row["checker_type"],
                    pkg_type=row["pkg_type"],
                )
            msg += utils.build_msg_per_error(row)
            with open(mailfile, "a") as writemail:
                writemail.write(msg)

    def _build_statistics(self):
        filename = utils.STATISTICS + "#" + self.default_contact.email
        mailfile = os.path.join(
            self.mailpath, filename + ".html"
        )
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
