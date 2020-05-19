import os
import csv
import smtplib
from configparser import ConfigParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ckan_pkg_checker.utils import utils

import logging
log = logging.getLogger(__name__)


class EmailSender():
    def __init__(self, rundir, configpath):
        config = ConfigParser()
        config.read(configpath)
        self.contactfile = utils._get_csvdir(rundir) / config.get(
                'contactchecker', 'csvfile')
        self.msgfile = utils._get_csvdir(rundir) / config.get(
                'linkchecker', 'msgfile')
        self.maildir = utils._get_maildir(rundir)
        self.sender = config.get('emailsender', 'sender')
        self.smtp_server = config.get('emailsender', 'smtp_server')
        self.bcc = config.get('emailsender', 'bcc')
        self.send_to_overwrite = config.get('emailsender', 'overwrite_send_to')
        self.admin = self.default_contact = utils.Contact(
            name=config.get('emailsender', 'admin_name'),
            email=config.get('emailsender', 'admin_email'))

    def build(self):
        fieldnames = utils.FieldNamesMsgFile
        with open(self.msgfile, 'r') as readfile:
            self.reader = csv.DictReader(readfile, fieldnames=fieldnames)
            headerline = next(self.reader)
            assert(','.join(headerline) == ','.join(fieldnames))
            for row in self.reader:
                self._process_line(row)

    def send(self):
        self._build_contactdir()
        for contact in os.listdir(self.maildir):
            path = os.path.join(self.maildir, contact)
            with open(path, 'rb') as readfile:

                text = MIMEText(readfile.read(), 'html', 'utf-8')
                msg = MIMEMultipart('alternative')

                msg['Subject'] = utils._get_email_subject()

                msg['From'] = self.sender
                send_from = self.sender

                msg['To'] = contact
                if self.send_to_overwrite:
                    send_to = [self.send_to_overwrite]
                else:
                    send_to = [self.sendtodir[contact].email]
                    if self.bcc:
                        msg['Bcc'] = self.bcc
                        send_to.append(self.bcc)

                msg.attach(text)
                server = smtplib.SMTP(self.smtp_server)
                server.sendmail(send_from, send_to, msg.as_string())
                server.quit()
                log.info("EMAIL OUTPUT:\nEmail for Contact: {}"
                         "\nwas sent to: {}\nSender is {}"
                         .format(contact, send_to, send_from)
                         )

    def _process_line(self, row):
        contacts = [utils.Contact(
            email=row['contact_email'], name=row['contact_name'])]
        contacts.append(self.admin)
        for contact in contacts:
            mailfile = os.path.join(self.maildir, contact.email)
            msg = ''
            if not os.path.isfile(mailfile):
                msg = utils._build_msg_per_contact(contact.name)
            msg += row['msg']
            with open(mailfile, 'a') as writemail:
                writemail.write(msg)

    def _build_contactdir(self):
        self.sendtodir = {}
        with open(self.contactfile, 'r') as readfile:
            fieldnames = utils.FieldNamesContactFile
            self.reader = csv.DictReader(readfile, fieldnames=fieldnames)
            headerline = next(self.reader)
            assert (','.join(headerline) == ','.join(fieldnames))
            self.sendtodir[self.admin.email] = self.admin
            for row in self.reader:
                self.sendtodir[row['contact_email']] = utils.Contact(
                    name=row['send_to_name'], email=row['send_to_email'])
