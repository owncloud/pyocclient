# -*- coding: utf-8 -*-
#
# vim: expandtab shiftwidth=4 softtabstop=4
#
from setuptools import setup

setup(
    name='pyocclient',
    version='0.1.0',
    author='Vincent Petry',
    author_email='pvince81@yahoo.fr',
    packages=['owncloudclient', 'owncloudclient.test'],
    url='https://github.com/PVince81/pyocclient/',
    license='LICENSE.txt',
    description='Python client library for ownCloud',
    long_description=open('README.rst').read(),
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
