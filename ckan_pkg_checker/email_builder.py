import csv
import os
import logging
from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailBuilder():
    def __init__(self, rundir, config):
        self.msgfile = utils.get_msgdir(rundir) / utils.get_config(config, 'messages', 'msgfile', required=True)
        self.maildir = utils.get_maildir(rundir)
        self.extra_message = {}
        for pkg_type in [utils.DCAT, utils.GEOCAT]:
            self.extra_message[pkg_type] = utils.get_config(config, 'extramessage', pkg_type)
        self.admin = self.default_contact = utils.Contact(
            name=utils.get_config(config, 'emailsender', 'admin_name', required=True),
            email=utils.get_config(config, 'emailsender', 'admin_email', required=True))

    def build(self):
        log.info("building emails")
        fieldnames = utils.FieldNamesMsgFile
        with open(self.msgfile, 'r') as readfile:
            self.reader = csv.DictReader(readfile, fieldnames=fieldnames)
            headerline = next(self.reader)
            assert(','.join(headerline) == ','.join(fieldnames))
            for row in self.reader:
                self._process_line(row)

    def _process_line(self, row):
        contacts = [utils.Contact(
            email=row['contact_email'], name=row['contact_name'])]
        if self.admin.email not in [contact.email for contact in contacts]:
            contacts.append(self.admin)
        for contact in contacts:
            pkg_type = row['pkg_type']
            mailfile = os.path.join(self.maildir, pkg_type + '#' + contact.email)
            msg = ''
            if not os.path.isfile(mailfile):
                if pkg_type in self.extra_message:
                    msg += self.extra_message[pkg_type]
                msg += utils.build_msg_per_contact(contact.name)
            msg += row['msg']
            with open(mailfile, 'a') as writemail:
                writemail.write(msg)
