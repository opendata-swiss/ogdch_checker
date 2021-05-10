# OGDCH Checker

## About 

This a tool for checking datasets and resources of a ckan installation.

- Emails can be send to the contacts of these datasets.
- The two steps: checking datasets and sending out emails can be separated 
  from each other
- There is a contactchecker, that writes the contacts of a dataset to a csv file
- There is a linkchecker which writes a linkchecker_msgs.csv file and a linkchecker.csv file
- the checker can be limited to a number of datasets (`--limit`) to one dataset (`--pkg`) or to and
  organization (`--org`)
- the checkers write `csv` files, since these can be easily used for data analysis (with jupyther notebooks)
- the checkers come with an interface, so it is fairly easy to add custom checkers as needed  
     
  
## Install 

```
git clone <repo>
python3 -m venv p3venv
source p3venv/bin/activate
pip install -r requirements.txt
```

## Deploy

Currently there is no deployment script in place for the ogdch_checker.
Just go ot the server:

```
ssh -p 22022 -l liip vps27.rs.bsa.oriented.ch
cd ogdch_checker
git fetch
git checkout master
``` 

## Usage

Just call the command with --help to get detailed instructions on how to use it:

```
python pkg_checker.py --help
``` 

The ogdch_checker currently runs as linkchecker once a month and
is entered in the crontab of the server:

```
5 0 4 * * /home/liip/checker_venv/bin/python3 /home/liip/ogdch_checker/pkg_checker.py --configpath /home/liip/ogdch_checker/config/production.ini --send
```

### Configuration files

There are two configuration files: one for development and one for production.
The package checker must always be called with a configuration file.

```
python pkg_checker.py --configpath config/development.ini
``` 

By default the command will perform the checks that are specified in the configuration
file and write csv files.

### Send and build emails

In order to send and build emails call it with `--send` or `--build`
You can combine this options to have the check and sending done in one go.
Or you can check first and send emails later. To send emails from a previous run,
use the name of that run and start the command withh `--run <runname> --send`.
You can also testrun the emails with `-t -s`: this does just log the emails, that would normally be send.

### Limit the scope of the package checker

You can restrict the checks and emailing on several levels:

- `--org <organization-slug>` restricts it to that organizations datasets
- `--limit <number>` restricts it to the first `<number>` of packages
- `--pkg <slug of a package>` restrict it to a single package

### Linkchecker-Emails

For the linkchecker emails only the linkchecker needs to be activated in the config files:

- LinkChecker: it checks the links for datasets and resources. 

It first tries the HEAD method and if this method fails it tries again with a GET request.

### The Run directory

Each run produces a directory in the tmp directory specified in the configuration file.
All information on that run is kept in that file including the logs, the csv files, that 
are written as results of the checks and also the mails that are build before they will be send.

So after the checker has run you can send or resend the emails with:

```
python pkg_checker.py --run <rundirectory name> --send
``` 

## Tests

To run the tests: 

```
pip install -r requirements.txt
```

After the installation you will be able to run the tests and see the current coverage.

```
coverage run -m unittest discover
coverage report
coverage html
```

## Setting up different emails for a contact

### Default

By default emails about failed link checks will be send to the contacts provided
in a dataset.

### Geocat

For datasets harvested by geocat, the emails are sent to the email provided for geocat in
the configuration file instead of the publisher of the dataset.

### Generalize this for other datasets

The email sending is decided by dataset type. In case there are other special dataset types this approach
can be easily generalize by writing also these dataset types to the files and adding special rules
in the email sender on where to send the emails for those other dataset types.
