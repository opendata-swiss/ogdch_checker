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


def _check_with_user_agent(test_url, http_method, user_agent):
    log.debug(f"URL {test_url} ({http_method}), User-Agent: {user_agent}")
    try:
        headers = {"User-Agent": user_agent}
        if http_method == "HEAD":
            req = requests.head(
                test_url,
                verify=False,  # SSL certificate will not be verified
                timeout=30,
                headers=headers,
            )
        elif http_method == "GET":
            req = requests.get(
                test_url,
                verify=False,  # SSL certificate will not be verified
                timeout=30,
                headers={
                    "Range": "bytes=0-10",  # Request the first 10 bytes
                    "User-Agent": user_agent,
                },
            )
        req.raise_for_status()
        log.info("Sent response %s" % req.status_code)
        return None  # Success, no error
    except requests.exceptions.HTTPError as e:
        log.debug(
            "HTTP EXCEPTION OCCURRED for URL %s (%s): %r" % (test_url, http_method, e)
        )
        # ignore 405 Method Not Allowed errors
        if 405 != e.response.status_code:
            return str(e)  # Return the error message
    except (ValueError, requests.exceptions.RequestException) as e:
        log.debug(
            "REQUEST EXCEPTION OCCURRED for URL %s (%s): %r"
            % (test_url, http_method, e)
        )
        if hasattr(e, "message") and hasattr(e.message, "reason"):
            return str(e.message.reason)
        else:
            return str(e)


def check_url_status(test_url, http_method="HEAD"):
    log.debug("URL %s (%s)" % (test_url, http_method))
    user_agents = [
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.3 "
            "Safari/537.36"
        ),
        "Custom",
    ]
    for user_agent in user_agents:
        error_result = _check_with_user_agent(test_url, http_method, user_agent)
        if not error_result:
            return None  # Success, no error
        else:
            log.debug(
                "Retrying with a different User-Agent for URL %s (%s)"
                % (test_url, http_method)
            )
    return error_result  # If all attempts fail


class RetryAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        super(RetryAdapter, self).__init__(*args, **kwargs)
        self.max_retries = Retry(
            total=3, backoff_factor=5, status_forcelist=[500, 502, 503, 504]
        )


session = requests.Session()
session.mount("http://", RetryAdapter())
session.mount("https://", RetryAdapter())
