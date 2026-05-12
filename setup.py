# /usr/bin/env python
import codecs
import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

setup(
    name='djangocms-named-menus',
    version='3.0.1',
    description='Allows you to add and edit custom named menus similar to Wordpress menus',
    long_description=README,
    long_description_content_type='text/markdown',
    author='Ryan Bagwell, Rogerio Carrasqueira, Michael Carder Ltd',
    license='MIT',
    url='https://github.com/mcldev/djangocms-named-menus',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=4.2,<5.0',
        'django-classy-tags',
        'django-cms>=3.11,<3.12',
        'django-autoslug>=1.7.2',
    ],
    extras_require={
        'test': [
            'djangocms-text-ckeditor>=5.1',
            'django-sekizai>=4.0',
        ],
    },
    python_requires='>=3.9',
    package_data={
        'readme': ['README.md'],
        'license': ['LICENSE']
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Framework :: Django CMS :: 3.11',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
