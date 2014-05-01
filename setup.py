# -*- coding: utf-8 -*-
#
# vim: expandtab shiftwidth=4 softtabstop=4
#
from setuptools import setup

version = '0.1'

long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('docs/source/CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(
    name='pyocclient',
    version=version,
    author='Vincent Petry',
    author_email='pvince81@yahoo.fr',
    packages=['owncloud', 'owncloud.test'],
    url='https://github.com/PVince81/pyocclient/',
    license='LICENSE.txt',
    description='Python client library for ownCloud',
    long_description=long_description,
    install_requires=[
        "requests >= 2.0.1",
    ],
	classifiers=[
		'Programming Language :: Python',
		'Development Status :: 3 - Alpha',
		'Environment :: Web Environment',
        'Intended Audience :: Developers',
		'Topic :: Internet :: WWW/HTTP',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'License :: OSI Approved :: MIT License'
	]
)
