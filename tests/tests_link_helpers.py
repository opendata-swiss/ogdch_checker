import unittest
from ckan_pkg_checker.link_helpers import _get_ckan_dataset_url, _get_ckan_resource_url


class TestResourceCheckMethods(unittest.TestCase):
    def setUp(self):
        self.pkg_name = 'my-test-package'
        self.resource_id = 'r42'
        self.siteurl = 'https://ckan-demo.org'

    def test__get_ckan_resource_url(self):
        resource_url_build = _get_ckan_resource_url(self.siteurl, self.pkg_name, self.resource_id)
        resource_url_expected = 'https://ckan-demo.org/dataset/my-test-package/resource/r42'
        self.assertEqual(resource_url_build, resource_url_expected)

    def test__get_ckan_dataset_url(self):
        dataset_url_build = _get_ckan_dataset_url(self.siteurl, self.pkg_name)
        dataset_url_expected = 'https://ckan-demo.org/dataset/my-test-package'
        self.assertEqual(dataset_url_build, dataset_url_expected)
