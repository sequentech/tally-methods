# This file is part of tally-methods.
# Copyright (C) 2013-2016  Sequent Tech Inc <legal@sequentech.io>

# tally-methods is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# tally-methods  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with tally-methods.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup

setup(
    name='tally-methods',
    version='7.1.0',
    author='Sequent Tech Inc',
    author_email='legal@sequentech.io',
    packages=['tally_methods', 'tally_methods.voting_systems'],
    scripts=[],
    url='https://github.com/sequentech/tally-methods',
    license='AGPL-3.0',
    description='sequent voting tally system',
    long_description=open('README.md').read(),
    install_requires=[]
)
