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

The validation of datasets uses [Shacl](https://www.w3.org/TR/shacl/) as a method and relies on
[pyshacl](https://github.com/RDFLib/pySHACL) as a tool.

An rdf version of the dataset is necessary to perform that check. If possible the rdf import
of the dataset is considered: for dataset that are harvested via dcat, the dataset is 
derived directly from the rdf harvest source by using the harvest source url.

For all other dataset the rdf version of the dataset on the ckan instance is used.
The rdf version of the dataset is derived via the extension ckanext-dcat as 
`<dataset-url>.rdf`.

Configuration Values: (as specified in the `[shaclchecker]` section of the configuration file)

- `shacl_file` (required): shacl file that is used to validate the datasets
- `csvfile` (required): filename for the file that stores the checker results as csv file
- `statfile`(required): filename for the file that stores the checker results statistics
- `frequency_file`(required): Turtle file that contains the check against the frequency vocabulary. This file is the `ònt_graph` that is needed for the pyshacl function `validate`

### Email Receivers

The checkers can be set to send out emails about the datasets, that failed the checks with the option `--send`.
The emails go to the contacts mentioned in the packages and additionally some administrators, that are set in the configuration file.
In case the contact for the metadata of an organization differs from the contact given in the packages, this can be specified in a csv file with the following fields:

```
pkg_type,organization_slug,contact_emails
geocat,example-org,example-contact1-email@gmail.com example-contact2-email@gmail.com
dcat,other-example-org,other-contact-email@org.ch
```

These fields are to be filled as follows:

- `pkg_type`: `geocat` for datasets that are harvested from https://geocat.ch, `dcat` for all other datasets
- `organization_slug`: slug of the organization on https://opendata.swiss
- `contact_emails`: metadata contacts for that organization: an email of a person of the organization that can change the metadata of datasets of that organization: more than one email can be added; separate emails by a blank
  
The emails for geocat datasets will be send to:

1. the contacts on the list if there are any
2. in case no contacts are on the list the contact-point specified in the dataset will be taken

The emails for dcat datasets will be send to:

1. the contacts on the list if there are any
2. in case no contacts are on the list the organization-admins will be taken as contacts
3. in case no organisation-admins are available the parent organization organization admins will be taken
4. in case there are still no contacts the contact-points specified in the dataset will be taken

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
python pkg_checker.py -c config.ini -p bauprojekte-immobilien1 -m shacl -b 

# checking a dataset on prod with the linkchecker and sending them
python pkg_checker.py -c config.ini -p bauprojekte-immobilien1 -m link -b -s

# checking all datasets on prod with the shaclchecker and sending the emails 
to a test address
python pkg_checker.py -c config.ini -m shacl -b -s -t
```

### Statistics Visualization

For how produce plots for Shacl and Linkchecker Statistics, see [here](statistics/README.md) 

## Tests and linting

We use Github Actions to automatically check the code for style and syntax
errors, and to run the tests. This is configured in `.github/workflows`.

To do this locally, first install the dev requirements.

```
pip install -r dev_requirements.txt
```

To run the tests and see the current coverage:

```
coverage run -m unittest discover
coverage report
coverage html
```

To check the code style and catch syntax errors:

```
isort --diff --check .
black --diff --check .
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics
```

To fix code style before committing your changes:

```
isort .
black .
```
