import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailSender():
    def __init__(self, rundir, config, test, mode):
        self.maildir = utils.get_maildir(rundir)
        self.sender = utils.get_config(config, 'emailsender', 'sender', required=True)
        self.smtp_server = utils.get_config(config, 'emailsender', 'smtp_server', required=True)
        self.bcc = utils.get_config(config, 'emailsender', 'bcc', fallback=None)
        self.admin = self.default_contact = utils.Contact(
            name=utils.get_config(config, 'emailsender', 'admin_name', required=True),
            email=utils.get_config(config, 'emailsender', 'admin_email', required=True))
        self.geocat_admin = utils.Contact(
            name=utils.get_config(config, 'emailsender', 'geocat_name', required=True),
            email=utils.get_config(config, 'emailsender', 'geocat_email', required=True))
        self.test = test
        if self.test:
            self.email_overwrites = utils.get_config(config, 'test', 'emails', required=True).split(' ')

    def send(self):
        log.info("sending emails")
        for filename in os.listdir(self.maildir):
            contact_type, contact_email = utils.process_msg_file_name(filename)
            path = os.path.join(self.maildir, filename)
            with open(path, 'rb') as readfile:
                text = MIMEText(readfile.read(), 'html', 'utf-8')
                msg = MIMEMultipart('alternative')

                msg['Subject'] = utils.get_email_subject()

                msg['From'] = self.sender
                send_from = self.sender

                msg['To'] = contact_email
                send_to = [self.admin.email]
                if contact_type == utils.GEOCAT:
                    send_to.append(self.geocat_admin.email)
                send_to.append(contact_email)
                if self.bcc:
                    msg['Bcc'] = self.bcc
                    send_to.append(self.bcc)

                msg.attach(text)
                server = smtplib.SMTP(self.smtp_server)
                if not self.test:
                    server.sendmail(send_from, send_to, msg.as_string())
                    server.quit()
                    utils.log_and_echo_msg(f"Email {filename} was sent to: {send_to} \n"
                                           f"send from: {send_from}\n"
                                           f"send info: msg['Bcc']: {msg['Bcc']}, msg['To']: {msg['To']}")
                else:
                    server.sendmail(send_from, self.email_overwrites, msg.as_string())
                    server.quit()
                    utils.log_and_echo_msg(f"Email {filename} was sent to: {self.email_overwrites} "
                                           f"would normally be sent to: {send_to}\n"
                                           f"send from: {send_from}\n"
                                           f"send info: msg['Bcc']: {msg['Bcc']}, msg['To']: {msg['To']}")
