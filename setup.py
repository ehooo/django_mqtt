from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup

import django_mqtt as meta

setup(name='django-mqtt',
      description='Send data to mqtt server as publisher.',
      version='.'.join(map(str, meta.__version__)),
      author=meta.__author__,
      author_email=meta.__contact__,
      url=meta.__homepage__,
      license=meta.__license__,
      keywords='django mqtt',
      classifiers=[
          "Framework :: Django",
          "Environment :: Web Environment",
          "Intended Audience :: Developers",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 2.7",
      ],
      packages=[
          'django_mqtt.*',
      ])
