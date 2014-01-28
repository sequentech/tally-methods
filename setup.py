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
