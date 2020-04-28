"""
Script to start the Worklogdb Application
"""
import click
from ckan_pkg_checker.pkg_checker import PackageCheck

@click.command()
@click.option('-l', '--limit', type=int,
              help='Number of packages to check.')
@click.option('-d', '--dry/--no-dry', default=False,
              help='This is a dry run')
@click.option('-t', '--tomail',
              help='Overwrites the recipients. Mail is only send to this address')
@click.option('-f', '--frommail',
              help='Overwrites the sender.')
def check_packages(dry=False, limit=None, tomail=None, frommail=None):
    """Script to test the resource links of a ckan installation"""
    check = PackageCheck(dry, limit, tomail, frommail)
    check.run()

if __name__ == '__main__':
    check_packages()
