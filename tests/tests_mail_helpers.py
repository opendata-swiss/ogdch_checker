import unittest
from ckan_pkg_checker.mail_helpers import (_get_recipient_overwrite, _get_sender,
    _build_msg_per_contact, _build_msg_per_error, _get_field_in_one_language)


class TestResourceCheckMethods(unittest.TestCase):
    def setUp(self):
        self.pkg_name = 'my-test-package'
        self.resource_id = 'r42'
        self.siteurl = 'https://ckan-demo.org'
        self.sender = 'some sender'
        self.overwrite = 'some overwrite'
        self.test_url = 'https://some-url'
        self.error_msg = 'Some 404 Error occured'
        self.receiver_name = 'Hans'
        self.dataset_url = 'https://ckan-site/dataset/some-dataset'
        self.title = 'download_url'
        self.resource_url = 'https://ckan-site/dataset/some-dataset/resource/r42'
        self.multi_language_field_filled = {'de': 'Haus', 'en': 'house', 'fr': '', 'it':''}
        self.multi_language_field_fr = {'de': '', 'en': 'house', 'fr': 'maison', 'it': ''}
        self.multi_language_field_en = {'de': '', 'en': 'house', 'fr': '', 'it': '?'}
        self.multi_language_field_it = {'de': '', 'en': '', 'fr': '', 'it': '?'}
        self.multi_language_field_empty = {'de': '', 'en': '', 'fr': '', 'it': ''}
        self.backup = 'Pferd'

    def test__get_sender_with_overwrite(self):
        sender_build = _get_sender(self.sender, self.overwrite)
        sender_expected = self.overwrite
        self.assertEqual(sender_build, sender_expected)

    def test__get_sender_without_overwrite(self):
        sender_build = _get_sender(self.sender, None)
        sender_expected = self.sender
        self.assertEqual(sender_build, sender_expected)

    def test__get_recipient_overwrite_with_overwrite(self):
        overwrite_build = _get_recipient_overwrite(self.sender)
        overwrite_expected = self.sender
        self.assertEqual(overwrite_build, overwrite_expected)

    def test__get_recipient_overwrite_without_overwrite(self):
        overwrite_build = _get_recipient_overwrite(None)
        overwrite_expected = None
        self.assertEqual(overwrite_build, overwrite_expected)

    def test__build_msg_per_contact(self):
        msg_per_contact_build = _build_msg_per_contact(self.receiver_name)
        msg_per_contact_expected = u'Hello Hans <br><br>\n\n[DE] - Wir haben ein Problem festgestellt beim Versuch, auf folgende Quellen zuzugreifen.<br>\nBitte kontrollieren Sie, ob diese Quellen noch zug&auml;nglich sind und korrigieren Sie sie n&ouml;tigenfalls.<br><br>\n\n' +\
        u'[FR] - Nous avons constat&eacute; un probl&egrave;me en essayant d&#39;acc&eacute;der aux ressources suivantes.<br>\nMerci de v&eacute;rifier si ces ressources sont toujours disponibles et de les corriger si n&eacute;cessaire.<br><br>\n\n' +\
        u'[IT] - Abbiamo riscontrato un problema nel tentativo di accedere alle risorse seguenti.<br>\nLa preghiamo di verificare se le risorse sono ancora disponibili e, se necessario, correggerle.<br><br>\n\n' + \
        u'[EN] - While accessing the following resources, we found some unexpected behaviour.<br>\nPlease check if those resources are still available.<br><br>\n\n-----<br><br>\n\n'
        self.assertEqual(msg_per_contact_build, msg_per_contact_expected)

    def test_get_field_in_one_language_filled(self):
        field_build = _get_field_in_one_language(self.multi_language_field_filled, self.backup)
        field_expected = 'Haus'
        self.assertEqual(field_build, field_expected)

    def test_get_field_in_one_language_backup(self):
        field_build = _get_field_in_one_language(self.multi_language_field_empty, self.backup)
        field_expected = 'Pferd'
        self.assertEqual(field_build, field_expected)

    def test_get_field_in_one_language_fr(self):
        field_build = _get_field_in_one_language(self.multi_language_field_fr, self.backup)
        field_expected = 'maison'
        self.assertEqual(field_build, field_expected)

    def test_get_field_in_one_language_en(self):
        field_build = _get_field_in_one_language(self.multi_language_field_en, self.backup)
        field_expected = 'house'
        self.assertEqual(field_build, field_expected)

    def test_get_field_in_one_language_it(self):
        field_build = _get_field_in_one_language(self.multi_language_field_it, self.backup)
        field_expected = '?'
        self.assertEqual(field_build, field_expected)

    def test__build_msg_per_error_with_resource_url(self):
        msg_per_error_build = _build_msg_per_error(self.test_url, self.error_msg, self.dataset_url, self.title, self.resource_url)
        msg_per_error_expected = u"Dataset: <a href='https://ckan-site/dataset/some-dataset'>download_url</a> (<a href='https://ckan-site/dataset/some-dataset/resource/r42'>resource detail page</a>) <br>\nAccessed URL: https://some-url <br>\nError Message: Some 404 Error occured <br><br>\n\n-----<br><br>\n\n"
        self.assertEqual(msg_per_error_build, msg_per_error_expected)

    def test__build_msg_per_error_without_resource_url(self):
        msg_per_error_build = _build_msg_per_error(self.test_url, self.error_msg, self.dataset_url, self.title)
        msg_per_error_expected = u"Dataset: <a href='https://ckan-site/dataset/some-dataset'>download_url</a><br>\nRelation URL: https://some-url <br>\nError Message: Some 404 Error occured <br><br>\n\n-----<br><br>\n\n"
        self.assertEqual(msg_per_error_build, msg_per_error_expected)

