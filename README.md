# OGDCH Checker

## About 

This a tool for checking datasets and resources of a ckan installation.
There are currently two checkers in place: 

- a linkchecker: checks link on datasets for their HTTP response codes (this 
  checker has a long run time, since it repeats requests, if they fail.)
- a shaclchecker that checks datasets against a shacl graph

For each run of the tool a temporary directory is set up to store the 
results of the run: 

- the tmp directory to store the runs is set up in the configuration
- the name of the run directory is derived from the current time and the run 
  parameters

In each run directory the following subdirectories are build by the tool

- `csv`: includes a csv file with raw results from each checker
- `msgs`: includes alls msgs in one file
- `mails`: here the messages are split up by contact 
- `logs`: includes and error log and and info log

### Geocat

Datasets that come to opendata.swiss via the geocat harvesters receive some 
special treatments:

- the contacts are derived differently

### Scope

The checkers can be run with a limited scope:

- `--org <organization-slug>` restricts it to that organizations datasets
- `--limit <number>` restricts it to the first `<number>` of packages
- `--pkg <slug of a package>` restrict it to a single package

### Instance

The checkers can be run on Prod, Abnahme or Test by specifying the URL of 
that instance (`--siteurl`)

### Checker Modes

The checker mode can be chosen: 

- `--mode shacl` runs the shacl checker
- `--mode link` runs the link checker

### Operation Modes

The tool can be called with different options to perform different steps:

By default emails are neither build (`mails` subdirectory) nor send.

Use:
- `--build`: to build the emails in the `mails` subdirectory
- `--send`: to also send them to the adresses specified in the `config.ini` file
- `--test`: sends the emails ot the emails specified in the `[test]` section of 
  the configuration file only
- `--run <runname> --send`: sends prebuild emails from a `mails` subdirectory: this option 
  can be used to split between email building and email sending 

### Linkchecker

- it checks the links for datasets and resources. 
- it first tries the HEAD 
  method and if this method fails it tries again with a GET request.

### ShaclChecker

See https://www.w3.org/TR/shacl/ for documentation on Shacl.
The shacl checker checks the datasets against a shacl graph that is 
specified in the `[shaclchecker]` section

It makes use of pyshacl: see here for a documentation: https://github.com/RDFLib/pySHACL
  
## Install 

```
git clone <repo>
python3 -m venv p3venv
source p3venv/bin/activate
pip install -r requirements.txt
cp config.ini.dist config.ini
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

Call the command with --help to get detailed instructions on how to use it:

```
python pkg_checker.py --help
```

Here you will find some common use cases as examples:

```
# checking a dataset on prod with the shaclchecker and building emails but not 
sending them
python pkg_checker.py --c config.ini -p bauprojekte-immobilien1 -m shacl -b 
-u https://ckan.opendata.swiss -b

# checking a dataset on prod with the linkchecker and sending them
python pkg_checker.py --c config.ini -p bauprojekte-immobilien1 -m link -b

# checking all datasets on prod with the shaclchecker and sending the emails 
to a test address
python pkg_checker.py --c config.ini -m shacl -s -t
```

## Tests

To run the tests: 

```
pip install -r dev_requirements.txt
```

After the installation you will be able to run the tests and see the current coverage.

```
coverage run -m unittest discover
coverage report
coverage html
```
