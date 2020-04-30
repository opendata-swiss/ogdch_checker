from urllib.parse import urljoin

def _get_ckan_resource_url(ckan_siteurl, pkg_name, resource_id):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name + '/resource/' + resource_id)

def _get_ckan_dataset_url(ckan_siteurl, pkg_name):
    return urljoin(ckan_siteurl, '/dataset/' + pkg_name)