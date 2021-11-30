import csv
import logging
import os
import pandas as pd

from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailBuilder:
    def __init__(self, rundir, mode, config):
        if mode == utils.MODE_SHACL:
            csvfile = utils.get_config(config, "shaclchecker", "csvfile", required=True)
        elif mode == utils.MODE_LINK:
            csvfile = utils.get_config(config, "linkchecker", "csvfile", required=True)

        import pdb; pdb.set_trace()
        self.csvfile = utils.get_csvdir(rundir) / csvfile
        self.maildir = utils.get_maildir(rundir)
        self.default_contact = utils.Contact(
            name=utils.get_config(
                config, "emailbuilder", "default_name", required=True
            ),
            email=utils.get_config(
                config, "emailbuilder", "default_email", required=True
            ),
        )
        self.statfilename = utils.get_config(config, "shaclchecker", "statfile", required=False)

    def build(self):
        utils.log_and_echo_msg("building emails")
        with open(self.csvfile, "r") as readfile:
            reader = csv.DictReader(readfile)
            for row in reader:
                self._process_line(row)

    def _process_line(self, row):
        contacts = [utils.Contact(email=row["contact_email"], name=row["contact_name"])]
        if self.default_contact.email not in [contact.email for contact in contacts]:
            contacts.append(self.default_contact)
        for contact in contacts:
            pkg_type = row["pkg_type"]
            mailfile = os.path.join(
                self.maildir, pkg_type + "#" + contact.email + ".html"
            )
            msg = ""
            if not os.path.isfile(mailfile):
                msg += utils.build_msg_per_contact(
                    receiver_name=contact.name,
                    checker_type=row["checker_type"],
                    pkg_type=row["pkg_type"],
                )
            msg += utils.build_msg_per_error(row)
            with open(mailfile, "a") as writemail:
                writemail.write(msg)

    def _build_stats(self):
        mailfile = os.path.join(
            self.maildir, 'statistics' + "#" + self.default_contact.email + ".html"
        )
        with open(mailfile, "a") as writemail:
            df = pd.read_csv(self.statfilename)
            stats = df.to_dict()
            msg = utils.build_stat_msg(
                receiver_name=self.default_contact.name,
                stats=stats,
            )
            writemail.write(msg)
