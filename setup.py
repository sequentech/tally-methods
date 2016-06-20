# This file is part of agora-tally.
# Copyright (C) 2013-2016  Agora Voting SL <agora@agoravoting.com>

# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup
from pip.req import parse_requirements

setup(
    name='Agora Tally',
    version='0.0.1',
    author='Eduardo Robles Elvira',
    author_email='edulix@wadobo.com',
    packages=['agora_tally', 'agora_tally.voting_systems'],
    scripts=[],
    url='http://pypi.python.org/pypi/agora_tally/',
    license='LICENSE.txt',
    description='agora voting tally system',
    long_description=open('README.md').read(),
    install_requires=[]
)
