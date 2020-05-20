# OGDCH Checker

## About 

This a tool for checking datasets and resources of a ckan installation.

- Emails can be send to the contacts of these datasets.
- The two steps: checking datasets and sending out emails can be separated 
  from each other
- There is a contactchecker, that can associate different receivers per dataset: 
  currently emails for datasets that are harvested by the geocat harvester go to 
  swisstopo
- the checker can be limited to a number of datasets (`--limit`) to one dataset (`--pkg`) or to and
  organization (`--org`)
- the checkers write `csv` files, since can easily used for data analysis (with jupyther notebooks)
  for example
- the checkers come with an interface, so it is fairly easy to add custom checkers as needed  
     
  
## Install 

```
git clone <repo>
python3 -m venv p3venv
source p3venv/bin/activate
cd ogdch-checker
pip install -r requirements.txt
```

## Usage

Just call the command with --help to get detailed instructions on how to use it:

```
python pkg_checker.py --help
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

### Limit the scope of the package checker

You can restrict the checks and emailing on several levels:

- `--org <organization-slug>` restricts it to that organizations datasets
- `--limit <number>` restricts it to the first `<number>` of packages
- `--pkg <slug of a package>` restrict it to a single package

### Checkers

Currently there are two checker classes that should both be activated in the configuration file.

- ContactChecker: it produces a list of contacts and where to send emails for these contacts. 

The background on this is that for geocat datasets emails should be send to geocat only.

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
