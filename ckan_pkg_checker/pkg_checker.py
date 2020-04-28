import ckanapi
import tempfile
import os
import smtplib
import yaml
import sys

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from requests_helpers import _check_url_status
from mail_helpers import _build_msg_per_error, _build_msg_per_contact, _get_field_in_one_language
from link_helpers import _get_ckan_resource_url, _get_ckan_dataset_url
from mail_helpers import _get_recipient_overwrite, _get_sender, EmailRecipient

import logging.handlers
log = logging.getLogger(__name__)


class PackageCheck():
    def __init__(self, dry, limit, tomail, frommail):
        self.config = self._build_config(dry, limit, tomail)
        self.ogdremote = ckanapi.RemoteCKAN(self.siteurl)
        self.geocat_pkg_ids = self._get_geocat_package_ids()
        self.result_cache = {}
        self.pkgs = self._get_packages()
        self.pkgs_count = len(self.pkgs)

    def run(self):
        for idx, id in enumerate(self.pkgs):
            log.info("#### (%s/%s) ##########################" % (idx + 1, self.pkgs_count))
            try:
                self._check_package(id)
            except Exception, e:
                log.exception('check_package failed {}'.format(e))
        self._send_mails()

    def _get_packages(self):
        try:
            pkgs = self.ogdremote.action.package_list()
        except Exception, e:
            log.exception('package_list failed')
            return []
        pkgs = [id for id in pkgs if not id.startswith('__')]
        if self.limit:
            return pkgs[:self.limit]
        return pkgs

    def _check_package(self, package_id):
        log.info('Package ID: [' + package_id + ']')
        pkg = self.ogdremote.action.package_show(id=package_id)
        if pkg['type'] == 'dataset':
            landing_page = pkg['url']
            if landing_page:
                self._check_url_status("landing_page_url", landing_page, pkg)

            if 'relations' in pkg:
                for relation in pkg['relations']:
                    relation_url = relation['url']
                    if relation_url:
                        self._check_url_status("relations_url", relation_url, pkg)

            for resource in pkg['resources']:
                self._check_resource(pkg, resource)

    def _check_resource(self, pkg, resource):
        resource_display_name = _get_field_in_one_language(resource['display_name'], resource['name'])
        log.info("--- (%s)" % (resource_display_name))
        resource_url = resource['url']
        try:
            download_url = resource['download_url']
        except KeyError:
            download_url = None
            pass

        if resource_url:
            self._check_url_status("resoure_url",
                resource_url, pkg,
                _get_ckan_resource_url(self.siteurl, pkg['name'], resource['id']))
        if download_url and download_url != resource_url:
            self._check_url_status("download_url",
                download_url, pkg,
                _get_ckan_resource_url(self.siteurl, pkg['name'], resource['id']))

    def _check_url_status(self, test_case, test_url, pkg, resource_url=None):
        if test_url in self.result_cache:
            previous_test_result = self.result_cache[test_url]
            if previous_test_result:
                log.info("\nREPEAT-ERROR at {}:{}, \nERROR-MSG: {}".format(test_case, test_url.encode('utf8'), previous_test_result))
                self._prepare_mail(test_url, previous_test_result, pkg, resource_url)
        new_test_result = _check_url_status(test_url)
        if new_test_result:
            log.info("\nERROR at {}:{}, \nERROR-MSG: {}".format(test_case, test_url.encode('utf8'), new_test_result))
            self._prepare_mail(test_url, new_test_result, pkg, resource_url)
            self.result_cache[test_url] = new_test_result

    def _prepare_mail(self, test_url, error_msg, pkg, resource_url=None):
        receivers = self._get_receivers_for_pkg(pkg)
        for receiver in receivers:
            fname = os.path.join(self.maildir, receiver.email)
            msg = ''
            if not os.path.isfile(fname):
                msg = _build_msg_per_contact(receiver.name)
            title = _get_field_in_one_language(pkg['title'], pkg['name'])
            dataset_url = _get_ckan_dataset_url(self.siteurl, pkg['name'])
            msg += _build_msg_per_error(test_url, error_msg, dataset_url, title, resource_url=None)
            mail = open(fname, 'a')
            try:
                mail.write(msg.encode('utf8'))
                log.info("Message written to %s" % fname)
            except:
                log.exception('failed to write mail: %s' % msg)

    def _get_receivers_for_pkg(self, pkg):
        if pkg['id'] in self.geocat_pkg_ids:
            return [self.geocat_recipient]
        elif pkg.get('contact_points',''):
            return [EmailRecipient(name=contact['name'], email=contact['email']) for contact in pkg['contact_points']]
        else:
            return [self.default_recipient]

    def _get_email_subject(self):
        return 'opendata.swiss : Automatische Kontrolle der Quellen / Controle automatique des ressources / Controllo automatico delle risorse / automatic ressource checker'

    def _send_mails(self):
        if not self.dryrun:
            subject = self._get_email_subject()
            for filename in os.listdir(self.maildir):
                try:
                    fp = open(self.maildir + filename, 'rb')
                    recipient = filename
                    text = MIMEText(fp.read(), 'html', 'utf-8')
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = self.sender
                    msg['To'] = recipient
                    if self.recipient_overwrite:
                        send_to = [self.recipient_overwrite]
                    else:
                        msg['Cc'] = self.cc_mail
                        send_to = [recipient, self.cc_mail]
                    msg.attach(text)
                    server = smtplib.SMTP(self.smtp_server)
                    server.sendmail(self.sender, send_to, msg.as_string())
                    server.quit()
                    log.debug("Mail sent to %s" % msg['To'])

                except IOError as e:
                    log.exception("Error occured while sending mails".format(e.message))
                except smtplib.SMTPResponseException as e:
                    log.exception("Error occured while sending mails {}: {}".format(e.smtp_code, e.smtp_error))

    def _get_geocat_package_ids(self):
        harvester_search_results = \
            self.ogdremote.action.package_search(fq='dataset_type:harvest AND source_type:geocat_harvester',
                                                 rows='100')
        geocat_harvester_ids = [h['id'] for h in harvester_search_results['results']]
        geocat_search_string = 'harvest_source_id:(' + ' OR '.join(geocat_harvester_ids) + ')'
        rows = 500
        page = 0
        geocat_pkg_ids = []
        result_count = 0
        while not geocat_pkg_ids or len(geocat_pkg_ids) < result_count:
            try:
                page = page + 1
                start = (page - 1) * rows
                result = self.ogdremote.action.package_search(fq=geocat_search_string, rows=rows, start=start)
                if not result_count:
                    result_count = result['count']
                geocat_pkg_ids.extend([pkg['id'] for pkg in result['results']])
            except Exception as e:
                if page == 1:
                    log.info('Error %s when searching for geocat packages' % e)
        log.info('Found %d geocat packages' % len(geocat_pkg_ids))
        log.info('Emails for those will be sent to {} at {}'.format(self.geocat_recipient.name, self.geocat_recipient.email))
        return geocat_pkg_ids

    def _build_config(self, dry=False, limit=None, tomail=None, frommail=None):
        try:
            with open('config.yaml') as file:
                defaults = yaml.load(file)
                self.logdir = defaults['log_dir']
                _setup_logging(logdir=self.logdir)
                self.maildir = _setup_mails(tmpdir=defaults['tmp_dir'])
                self.sender = _get_sender(defaults['default_sender_mail'], frommail)
                self.recipient_overwrite = _get_recipient_overwrite(tomail)
                self.dryrun = dry
                self.geocat_recipient = EmailRecipient(name=defaults['geocat_mail'], email=defaults['geocat_name'])
                self.default_recipient = EmailRecipient(name=defaults['default_recipient_mail'], email=defaults['default_recipient_name'])
                self.smtp_server = defaults['smtp_server']
                self.siteurl = defaults['site_url']
                self.cc_mail = defaults['cc_mail']
                self.limit = limit
                self._log_config()
        except IOError as e:
            print(e)
            sys.exit()

    def _log_config(self):
        log.info("============ Configuration ==============")
        log.info("site url                : {}".format(self.siteurl))
        log.info("Logs at:                : {}".format(self.logdir))
        log.info("Mails at:               : {}".format(self.maildir))
        log.info("Sender                  : {}".format(self.sender))
        if self.dryrun:
            log.info("This is a dryrun! No mails will be send!")
        elif self.recipient_overwrite:
            log.info("Recipients overwrite    : {}".format(self.recipient_overwrite))
        else:
            log.info("geocat-recipient        : {} {}".format(self.geocat_recipient.name, self.geocat_recipient.email))
            log.info("default-recipient       : {} {}".format(self.default_recipient.name, self.default_recipient.email))
            log.info("cc to                   : {}".format(self.maildir))
        log.info("Limit nr of packages      : {}".format(self.limit))
        log.info("smtp server               : {}".format(self.smtp_server))
        log.info("============ /Configuration =============")

def _setup_logging(logdir):
    logfile = os.path.join(logdir, 'resource_test.log')
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=(1048576*5), backupCount=7
    )
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    sterr_handler = logging.StreamHandler()
    sterr_handler.setFormatter(formatter)
    log.addHandler(sterr_handler)

def _setup_mails(tmpdir):
    tmp_dir = tempfile.mkdtemp(dir=tmpdir)
    mail_dir = os.path.join(tmp_dir, 'mails/')
    os.makedirs(mail_dir)
    return mail_dir
