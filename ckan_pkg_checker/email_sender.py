import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ckan_pkg_checker.utils import utils

log = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, rundir, config, test, mode):
        self.maildir = utils.get_maildir(rundir)
        self.sender = utils.get_config(config, "emailsender", "sender", required=True)
        self.smtp_server = utils.get_config(
            config, "emailsender", "smtp_server", required=True
        )
        self.cc = utils.get_config(config, "emailsender", "cc", required=True)
        bcc = utils.get_config(config, "emailsender", "bcc", required=True)
        geocat_admin = utils.get_config(
            config, "emailsender", "geocat_admin", required=True
        )
        self.add_as_receivers_for_dcat = [self.cc, bcc]
        self.add_as_receivers_for_geocat = [self.cc, bcc, geocat_admin]
        self.test = test
        if self.test:
            self.email_overwrites = utils.get_config(
                config, "test", "emails", required=True
            ).split(" ")

    def send(self):
        log.info("sending emails")
        for filename in os.listdir(self.maildir):
            contact_type, contact_email = utils.process_msg_file_name(filename)
            path = os.path.join(self.maildir, filename)
            with open(path, "rb") as readfile:
                text = MIMEText(readfile.read(), "html", "utf-8")
                msg = MIMEMultipart("alternative")

                msg["Subject"] = utils.get_email_subject()

                msg["From"] = self.sender
                send_from = self.sender

                msg["To"] = contact_email
                msg["Cc"] = self.cc

                send_to = [contact_email]
                if contact_type == utils.GEOCAT:
                    send_to.extend(self.add_as_receivers_for_geocat)
                else:
                    send_to.extend(self.add_as_receivers_for_dcat)

                msg.attach(text)
                server = smtplib.SMTP(self.smtp_server)
                if not self.test:
                    server.sendmail(send_from, send_to, msg.as_string())
                    server.quit()
                    utils.log_and_echo_msg(
                        f"Email {filename} was sent to: {send_to} \n"
                        f"send from: {send_from}\n"
                        f"send info: msg['Bcc']: {msg['Bcc']}, msg['To']: {msg['To']}"
                    )
                else:
                    server.sendmail(send_from, self.email_overwrites, msg.as_string())
                    server.quit()
                    utils.log_and_echo_msg(
                        f"Email {filename} was sent to: {self.email_overwrites} "
                        f"would normally be sent to: {send_to}\n"
                        f"send from: {send_from}\n"
                        f"send info: msg['Bcc']: {msg['Bcc']}, msg['To']: {msg['To']}"
                    )
