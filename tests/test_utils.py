import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from ckan_pkg_checker.utils import utils


class TestResourceCheckMethods(unittest.TestCase):
    def setUp(self):
        self.pkg_name = "my-test-package"
        self.resource_id = "r42"
        self.siteurl = "https://ckan-demo.org"
        self.test_url = "https://some-url"
        self.error_msg = "Some 404 Error occured"
        self.receiver_name = "Hans"
        self.dataset_url = "https://ckan-site/dataset/some-dataset"
        self.title = "download_url"
        self.resource_url = "https://ckan-site/dataset/some-dataset/resource/r42"
        self.multi_language_field_filled = {
            "de": "Haus",
            "en": "house",
            "fr": "",
            "it": "",
        }
        self.multi_language_field_fr = {
            "de": "",
            "en": "house",
            "fr": "maison",
            "it": "",
        }
        self.multi_language_field_en = {"de": "", "en": "house", "fr": "", "it": "?"}
        self.multi_language_field_it = {"de": "", "en": "", "fr": "", "it": "?"}
        self.multi_language_field_empty = {"de": "", "en": "", "fr": "", "it": ""}
        self.backup = "Pferd"
        self.rundir = Path("/home/")
        self.person1_name = "Person1"
        self.person1_email = "person1@org.ch"
        self.person2_name = "Person2"
        self.person2_email = "person2@org.ch"
        self.package_contact_points = [
            {"name": self.person1_name, "email": self.person1_email},
            {"name": self.person2_name, "email": self.person2_email},
        ]

    def test__get_field_in_one_language_filled(self):
        field_build = utils.get_field_in_one_language(
            self.multi_language_field_filled, self.backup
        )
        field_expected = "Haus"
        self.assertEqual(field_build, field_expected)

    def test__get_field_in_one_language_backup(self):
        field_build = utils.get_field_in_one_language(
            self.multi_language_field_empty, self.backup
        )
        field_expected = "Pferd"
        self.assertEqual(field_build, field_expected)

    def test__get_field_in_one_language_fr(self):
        field_build = utils.get_field_in_one_language(
            self.multi_language_field_fr, self.backup
        )
        field_expected = "maison"
        self.assertEqual(field_build, field_expected)

    def test__get_field_in_one_language_en(self):
        field_build = utils.get_field_in_one_language(
            self.multi_language_field_en, self.backup
        )
        field_expected = "house"
        self.assertEqual(field_build, field_expected)

    def test__get_field_in_one_language_it(self):
        field_build = utils.get_field_in_one_language(
            self.multi_language_field_it, self.backup
        )
        field_expected = "?"
        self.assertEqual(field_build, field_expected)

    def test__get_csvdir(self):
        csvdir = utils.get_csvdir(self.rundir)
        self.assertEqual(csvdir, self.rundir / "csv")

    def test__get_maildir(self):
        csvdir = utils.get_maildir(self.rundir)
        self.assertEqual(csvdir, self.rundir / "mails")

    def test__get_logdir(self):
        csvdir = utils.get_logdir(self.rundir)
        self.assertEqual(csvdir, self.rundir / "logs")

    def test_get_ckan_dataset_url(self):
        dataset_url = utils.get_ckan_dataset_url(self.siteurl, self.pkg_name)
        expected_url = urljoin(self.siteurl, "/dataset/" + self.pkg_name)
        self.assertEqual(dataset_url, expected_url)

    def test_get_ckan_resource_url(self):
        resource_url = utils.get_ckan_resource_url(
            self.siteurl, self.pkg_name, self.resource_id
        )
        expected_url = urljoin(
            self.siteurl, "/dataset/" + self.pkg_name + "/resource/" + self.resource_id
        )
        self.assertEqual(resource_url, expected_url)

    def test_get_pkg_contacts(self):
        recipients = utils.get_pkg_contacts(self.package_contact_points)
        expected_recipients = [
            utils.Contact(self.person1_name, self.person1_email),
            utils.Contact(self.person2_name, self.person2_email),
        ]
        self.assertListEqual(recipients, expected_recipients)

    def test__get_runname(self):
        runname = utils._get_runname(org="orgname", pkg=None, mode="shacl", limit="")
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        self.assertEqual(f"{timestamp}-shacl-org-orgname", runname)

    def test__get_email_subject(self):
        email_subject = utils.get_email_subject(mode=utils.MODE_SHACL)
        expected_email_subject = utils.EMAIL_SUBJECT_SHACL
        self.assertEqual(email_subject, expected_email_subject)

    def test__process_msg_file_name(self):
        filename = "geocat#max.moore@swisstopo.ch.html"
        contact_type, contact_mail = utils.process_msg_file_name(filename)
        self.assertEqual(contact_type, "geocat")
        self.assertEqual(contact_mail, "max.moore@swisstopo.ch")
