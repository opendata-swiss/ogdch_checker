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
        self.email_subject = utils.get_email_subject(mode=mode)
        self.email_subject_statistics = utils.get_email_subject_statistics(mode=mode)
        self.email_subject_contact_statistics = utils.get_email_subject_contact_statistics(mode=mode)
        self.test = test
        if self.test:
            self.email_overwrites = utils.get_config(
                config, "test", "emails", required=True
            ).split(" ")

    def send(self):
        log.info("sending emails")
        for filename in os.listdir(self.maildir):
            utils.log_and_echo_msg(f"processing {filename}")
            contact_type, contact_email = utils.process_msg_file_name(filename)
            path = os.path.join(self.maildir, filename)
            with open(path, "rb") as readfile:
                text = MIMEText(readfile.read(), "html", "utf-8")
                msg = MIMEMultipart("alternative")
                if contact_type == utils.STATISTICS:
                    msg["Subject"] = self.email_subject_statistics
                elif contact_type == utils.CONTACTS_STATISTICS:
                    msg["Subject"] = self.email_subject_contact_statistics
                else:
                    msg["Subject"] = self.email_subject

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

                if self.test:
                    receivers = self.email_overwrites
                else:
                    receivers = send_to

                server = smtplib.SMTP(self.smtp_server)
                try:
                    server.sendmail(send_from, receivers, msg.as_string())
                except Exception as e:
                    utils.log_and_echo_msg(
                        f"Error {e} occured while sending email {filename}, error=True"
                    )
                else:
                    utils.log_and_echo_msg(
                        f"Email {filename} send from {send_from} to {receivers} intended for {send_to}"
                    )
                finally:
                    server.quit()
