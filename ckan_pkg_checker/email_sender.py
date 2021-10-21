import os
import csv
import click
import smtplib
from configparser import ConfigParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ckan_pkg_checker.utils import utils

import logging
log = logging.getLogger(__name__)


class EmailSender():
    def __init__(self, rundir, configpath, test):
        config = ConfigParser()
        config.read(configpath)
        self.msgfile = utils._get_msgdir(rundir) / config.get(
            'messages', 'msgfile')
        self.maildir = utils._get_maildir(rundir)
        self.sender = config.get('emailsender', 'sender')
        self.smtp_server = config.get('emailsender', 'smtp_server')
        self.bcc = config.get('emailsender', 'bcc')
        self.send_to_overwrite = config.get('emailsender', 'overwrite_send_to', fallback=None)
        self.admin = self.default_contact = utils.Contact(
            name=config.get('emailsender', 'admin_name'),
            email=config.get('emailsender', 'admin_email'))
        self.geocat_admin = utils.Contact(
            name=config.get('emailsender', 'geocat_name'),
            email=config.get('emailsender', 'geocat_email'))
        self.test = test

    def build(self):
        log.info("building emails")
        fieldnames = utils.FieldNamesMsgFile
        with open(self.msgfile, 'r') as readfile:
            self.reader = csv.DictReader(readfile, fieldnames=fieldnames)
            headerline = next(self.reader)
            assert(','.join(headerline) == ','.join(fieldnames))
            for row in self.reader:
                self._process_line(row)

    def send(self):
        log.info("sending emails")
        for filename in os.listdir(self.maildir):
            contact_type, contact_email = utils._process_msg_file_name(filename)
            path = os.path.join(self.maildir, filename)
            with open(path, 'rb') as readfile:

                text = MIMEText(readfile.read(), 'html', 'utf-8')
                msg = MIMEMultipart('alternative')

                msg['Subject'] = utils._get_email_subject()

                msg['From'] = self.sender
                send_from = self.sender

                msg['To'] = contact_email
                send_to = [self.admin.email]
                if contact_type == utils.GEOCAT:
                    send_to.append(self.geocat_admin.email)
                else:
                    send_to.append(contact_email)
                if self.bcc:
                    msg['Bcc'] = self.bcc
                    send_to.append(self.bcc)

                msg.attach(text)
                if not self.test:
                    server = smtplib.SMTP(self.smtp_server)
                    server.sendmail(send_from, send_to, msg.as_string())
                    server.quit()
                log_msg = "Email {} was sent to: {} from: {}, msg['Bcc']: {}, msg['To']: {}, msg['From']: {}"\
                          .format(filename, send_to, send_from, msg['Bcc'], msg['To'], msg['From'])
                log.info(log_msg)
                click.echo(log_msg)

    def _process_line(self, row):
        contacts = [utils.Contact(
            email=row['contact_email'], name=row['contact_name'])]
        if not self.admin.email in [contact.email for contact in contacts]:
            contacts.append(self.admin)
        for contact in contacts:
            mailfile = os.path.join(self.maildir, row['pkg_type'] + '#' + contact.email)
            msg = ''
            if not os.path.isfile(mailfile):
                msg = utils._build_msg_per_contact(contact.name)
            msg += row['msg']
            with open(mailfile, 'a') as writemail:
                writemail.write(msg)
