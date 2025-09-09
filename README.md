# OGDCH Checker

## About 

This a tool for checking datasets and resources of a ckan installation.
There are currently two checkers in place: 

- a linkchecker: checks link on datasets for their HTTP response codes (this 
  checker has a long run time, since it repeats requests, if they fail.)
- a shaclchecker that checks datasets against a shacl graph (the shacl graph can be set in the configuration).

## Install

```
git clone git@github.com:opendata-swiss/ogdch_checker.git
cd ogdch_checker
python3 -m venv p3venv
source p3venv/bin/activate
pip install wheel
pip install -r requirements.txt
cp config.ini.dist config.ini
cp .env.dist .env
```

### Secrets

- Fill in a sysadmin ckan api key into `.env`. This must be a sysadmin api key for the ckan site specified in `[site] site_url` in the `config.ini`

### Configuration
In the configuration file `config.ini`:

- replace the absolute path `/home/liip/tmp` by your own path to a store the output of the ogdch_checker runs: the directory must exist
- replace the absolute path `/home/liip/ogdch_checker` by your own absolute path to the ogdch_checker
- in `[contacts]` the `csvfile` can also be left empty, as it is optional

Once you have filled in the configuration, you are ready to start your first run:

## Usage

Call the command with --help to get detailed instructions on how to use it:

```
python pkg_checker.py --help
```

See further down for a more detailed explanation of the options.

### Usage examples

Here you will find some common use cases as examples:

checking for a dataset with the shaclchecker and building emails but not sending them
```
python pkg_checker.py -c config.ini -p bauprojekte-immobilien1 -m shacl -b 
```

checking the organization with the linkchecker and building but not sending emails
```
python pkg_checker.py -c config.ini -o bernmobil -m link -b
```

### Output

The command will put most output on the terminal as well as in the logs. 
In general per run a rundir is written and all output for the run is gathered in that run directory:

For each run of the command a temporary directory is set up in the `[tmpdir] tmppath` that was specified in the `config.ini` file

The run name is formed from the arguments of the run. 
In the directory: `<tmpdir>/<runname>` the following subdirectories can be found:

- `logs`: a log of the run that includes the paramters and configuration it was started with an errors in case they occured
- `csv`: here are the raw results of each checker are stored as csv files: each error that occured gets a row in there
- `mails`: this directory stores all mails that will get send out in a file with the receiver as file name

### Command Options

#### Mandatory Options

The configuration path must always be set:

`-c, --configpath <config path>`  Path to the config file. Example `-c config.ini`

Also the mode must be set: it decides which checker to run: 

- linkchecker: `link`
- shaclchecker: `shacl`

`-m, --mode <mode>`  Mode: LinkChecker `link` or ShaclChecker `shacl`Example `--m link`

#### Scope Options

By default the scope of the check will be the whole site.
With these parameters you can reduce on the scope of the checker:

`-l, --limit <int>`Limit the number of packages to check. Example: `--limit 20`

`-p, --pkg <slug>>` Check only a single package. Example: `--pkg vbz- haltestellen`

`-o, --org <slug>`  Check only a single organization. Example `--org bernmobil`

`-ht, --harvestertype <slug>`  Check only datasets harvested by a specific harvester type (e.g., geocat or dcat). Example `--harvestertype geocat`

#### Step Options

With these paramter you can decide about which steps should be run by the checkers:
These steps exist for the checkers:

| Step            | Description                          | Input dir | output dir |
|-----------------|--------------------------------------|-----------|------------|
| perform checks  | checks datasets and writes csv files | -     `   | csv        |
| build emails    | builds emails as files               | csv       | mails      |
| send emails     | sends files as emails                | mails     | -          |

These steps can be run on their own, if the required input exists. 
In case of skipping the fist step, the rundirectory argument must be specified:

```
-r, --run TEXT            Run directory name to use for the build and send
                          of mails. Example --run 2022-11-28-2104-shacl.
                          This assumes the checker has run before and has
                          set up a directory with results of that run. With
                          this option mails can be build and send out from
                          the results of a previous checker run.
```

By default on the checking step is run. The other steps need to be added as options on the command.

The step options are:

Build email:
```
  -b, --build / --no-build  Build the mails in the mails directory. Example
                            --build.By default the build is not performed.
```

Send email: With `-s` emails are sent to the receivers specified in the `config.ini` `[emailsender]` section.
The email receivers can be overwriten with the receivers specified in the `[test]` section by using the option `-s`  

```
  -s, --send / --no-send    Send the emails from the mail directory. Example:
                            --send.By default the mails are not send.
  -t, --test / --no-test    Tests the sending of emails by logging instead of
                            sendingExample: --test.
```

Common step combinations are: 

| Option           | Action                                                          | 
|------------------|-----------------------------------------------------------------|
| `-b -s`          | run checks and send emails                                      |
| `-b`             | build but don't send email                                      |
| `-r <rundir> -s` | sends emails  from a run dircectory that has been build  before |          |
| `-b -s -t`       | build and send emails to a test receiver                        |  

Here are some common use cases:

## Details on the checkers

### Linkchecker

- it checks the links for datasets and resources.
- it first tries the HEAD
  method and if this method fails it tries again with a GET request.

### ShaclChecker

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
4. in case there are still no contacts the dcat_admin email will be taken from the config file

### Statistics

The checker sends additional emails with some statistics about each run to the default contact.
The followings statistics will be emailed:

- a list of checks that have been performed together with the counts of how often the errors occured
- a list of organizations with the contacts that have been informed together with the counts of errors that have been reported to them

#### Statistics Visualization

For how produce plots for Shacl and Linkchecker Statistics, see [here](statistics/README.md)

## Deploy

The ogdch_checker is deployed via github actions.

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
