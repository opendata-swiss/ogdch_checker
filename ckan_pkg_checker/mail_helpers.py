from urlparse import urljoin
from collections import namedtuple

EmailRecipient = namedtuple('EmailRecipient', ['name', 'email'])

def _get_sender(sender, overwrite=None):
    if overwrite:
        return overwrite
    else:
        return sender

def _get_recipient_overwrite(overwrite):
    if overwrite:
        return overwrite
    return None

def _build_msg_per_contact(receiver_name):
    msg = u'Hello %s <br><br>\n\n' % receiver_name

    msg += u'[DE] - Wir haben ein Problem festgestellt beim Versuch, auf folgende Quellen zuzugreifen.<br>\n'
    msg += u'Bitte kontrollieren Sie, ob diese Quellen noch zug&auml;nglich sind und korrigieren Sie sie n&ouml;tigenfalls.<br><br>\n\n'

    msg += u'[FR] - Nous avons constat&eacute; un probl&egrave;me en essayant d&#39;acc&eacute;der aux ressources suivantes.<br>\n'
    msg += u'Merci de v&eacute;rifier si ces ressources sont toujours disponibles et de les corriger si n&eacute;cessaire.<br><br>\n\n'

    msg += u'[IT] - Abbiamo riscontrato un problema nel tentativo di accedere alle risorse seguenti.<br>\n'
    msg += u'La preghiamo di verificare se le risorse sono ancora disponibili e, se necessario, correggerle.<br><br>\n\n'

    msg += u'[EN] - While accessing the following resources, we found some unexpected behaviour.<br>\n'
    msg += u'Please check if those resources are still available.<br><br>\n\n'

    msg += u'-----<br><br>\n\n'
    return msg

def _build_msg_per_error(test_url, error_msg, dataset_url, title, resource_url=None):
    msg = u"Dataset: <a href='%s'>%s</a>" % (dataset_url, title)
    if resource_url:
        resource_url = resource_url.encode('utf8')
        msg += u" (<a href='%s'>resource detail page</a>) <br>\n" % resource_url
        msg += u'Accessed URL: %s <br>\n' % test_url
    else:
        msg += u'<br>\n'
        msg += u'Relation URL: %s <br>\n' % test_url
    msg += u'Error Message: %s <br><br>\n\n-----<br><br>\n\n' % unicode(error_msg, 'utf8')
    return msg

def _get_field_in_one_language(multi_language_field, backup):
    if multi_language_field.get('de'):
        return multi_language_field['de']
    elif multi_language_field.get('fr'):
        return multi_language_field['fr']
    elif multi_language_field.get('en'):
        return multi_language_field['en']
    elif multi_language_field.get('it'):
        return multi_language_field['it']
    else:
        return backup
