import logging

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import (
    InsecurePlatformWarning,
    InsecureRequestWarning,
)
from requests.packages.urllib3.util.retry import Retry

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)

log = logging.getLogger(__name__)


def check_url_status(test_url, http_method="HEAD"):
    log.debug("URL %s (%s)" % (test_url, http_method))
    error_result = None
    try:
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/55.0.2883.75 "
            "Safari/537.36"
        )
        req = session.request(
            http_method,
            test_url,
            verify=False,
            timeout=30,
            headers={"User-Agent": user_agent},
        )
        req.raise_for_status()
        log.info("sent response %s" % req.status_code)
    except requests.exceptions.HTTPError as e:
        log.debug(
            "HTTP EXCEPTION OCCURED for URL %s (%s): %r" % (test_url, http_method, e)
        )
        # ignore 405 Method Not Allowed errors
        if 405 != e.response.status_code:
            error_result = str(e)
    except (ValueError, requests.exceptions.RequestException) as e:
        log.debug(
            "REQUEST EXCEPTION OCCURED for URL %s (%s): %r" % (test_url, http_method, e)
        )
        try:
            error_result = str(e.message.reason)
        except AttributeError:
            error_result = str(e)

    if error_result:
        return error_result


class RetryAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        super(RetryAdapter, self).__init__(*args, **kwargs)
        self.max_retries = Retry(
            total=3, backoff_factor=5, status_forcelist=[500, 502, 503, 504]
        )


session = requests.Session()
session.mount("http://", RetryAdapter())
session.mount("https://", RetryAdapter())
