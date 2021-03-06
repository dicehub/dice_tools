import os
from setuptools import setup, find_packages

__VERSION__ = "18.01.0"

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
        'py-lz4framed',
        'msgpack-python'],
)
