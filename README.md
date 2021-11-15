# OGDCH Checker

## About 

This a tool for checking datasets and resources of a ckan installation.
There are currently two checkers in place: 

- a linkchecker: checks link on datasets for their HTTP response codes (this 
  checker has a long run time, since it repeats requests, if they fail.)
- a shaclchecker that checks datasets against a shacl graph (the shacl graph can be set in the configuration).

For each run of the tool a temporary directory is set up to store the 
results of the run: 

The run name formed of the arguments of the run. In the directory: `<tmpdir>/<runname>` the following subdirectories can be found:

- `csv`: includes a csv file with raw results from each checker
- `mails`: here the messages are split up by contact and provided as html files
- `logs`: includes and error log and an info log: the error log contains setup errors if they occured and will otherwise be empty.

### Scope

The checkers are checking the ckan site `https://ckan.opendata.swiss` and its test instances.
They can be run with the following scopes:

- default: check all datasets on the site
- `--org <organization-slug>` restricts to the datasets of one organization
- `--limit <number>` restricts it to the first `<number>` of packages
- `--pkg <slug of a dataset>` restrict it to a single dataset

### Configuration

There is a [`config.ini.dist`](config.ini.dist) file to explain the configuration

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


### Checker Modes

The checker mode can be chosen: 

- `--mode shacl` runs the shacl checker
- `--mode link` runs the link checker

#### Linkchecker

- it checks the links for datasets and resources. 
- it first tries the HEAD 
  method and if this method fails it tries again with a GET request.

#### ShaclChecker

See https://www.w3.org/TR/shacl/ for documentation on Shacl.
The shacl checker checks the datasets against a shacl graph that is 
specified in the `[shaclchecker]` section

It makes use of pyshacl: see here for a documentation: https://github.com/RDFLib/pySHACL

### Contacts

Datasets that come to opendata.swiss via the geocat harvesters receive some 
special treatments:

- the contacts are derived differently
  
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

# checking a dataset on prod with the linkchecker and sending them
python pkg_checker.py --c config.ini -p bauprojekte-immobilien1 -m link -b

# checking all datasets on prod with the shaclchecker and sending the emails 
to a test address
python pkg_checker.py --c config.ini -m shacl -b -s -t
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
