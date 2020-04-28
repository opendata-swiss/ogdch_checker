# OGDCH Checker

Check for all packages:

- url to landing page
- url of relations

Checks for all resources:

- download url
- resource url

Errors are reported per email to the following recipients:

- contact points of the dataset

Exception 1: Datasets that come in through the geocat harvester are reported to Swisstopo
Exception 2: Datasets that have no contact are reported to the default recipient 

All outgoing emails can be directed to an email overwrite by the argument --tomail.
With the Option --dry t no emails will be send.

Emails are written to a temporary folder first. Sending them means reading these files 
per recipient and then sending them according to the options and configuration.

## Install 

```
git clone <repo>
virtualenv p2venv 
source p2venv/bin/activate
cd ogdch-checker
pip install -r requirements.txt
``` 

## Usage:

```
python pkg-checker.py [--dry] [--limit number-of-packages] [--tomail overwrite-recipient-email]
``` 
Options:
    -h, --help                     Show this help message and exit.
    -d, --dry t                    a.k.a. Debug. Run Tests, generate Error-Mails without sending them.
    -l, --limit <number-of-pkgs>   Limit the amount of packages this script handles
    -t, --tomail <recipient-email> Email address of recipient

Configuration: expected in config.yaml:

- default_sender_mail: email sender
- default_recipient_mail: default email recipient (if data packages don't have a contact)
- default_recipient_name: name of default email recipient
- cc_mail: cc all outgoing email to this address
- geocat_mail: contact for datasets harvested by geocat_harvester
- geocat_name: name of contact for geocat datasets
- smtp_server: mailserver
- site_url: site to check
- log_dir: absolute path to log directory
- tmp_dir: absolute path to mail directory


### Example:

```
python pkg_checker.py --dry t --limit 20
``` 

## Tests

coverage run -m unittest discover
coverage report
coverage html