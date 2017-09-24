from setuptools import setup, find_packages
from dice_tools import __VERSION__
import os

with open('README.md') as f:
    long_description = f.read()

setup(
    name='dice_tools',
    version=__VERSION__,
    author='DICEhub',
    author_email='info@dicehub.com',
    description='DICE application tools',
    long_description=long_description,
    url='http://dicehub.com',
    packages = find_packages(),
    install_requires=[
        'PyYAML',
        'greenlet',
        'msgpack-python'],
)
