#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ) as fh:
        return fh.read()


setup(
    name="dvg-pyqt-filelogger",
    version="1.4.0",
    license="MIT",
    description="PyQt interface to handle logging data to file particularly well suited for multithreaded programs.",
    long_description="%s\n%s"
    % (
        re.compile("^.. start-badges.*^.. end-badges", re.M | re.S).sub(
            "", read("README.rst")
        ),
        re.sub(":[a-z]+:`~?(.*?)`", r"``\1``", read("CHANGELOG.rst")),
    ),
    long_description_content_type="text/x-rst",
    author="Dennis van Gils",
    author_email="vangils.dennis@gmail.com",
    url="https://github.com/Dennis-van-Gils/python-dvg-pyqt-filelogger",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Scientific/Engineering ",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
    project_urls={
        "Issue Tracker": "https://github.com/Dennis-van-Gils/python-dvg-pyqt-filelogger/issues",
    },
    keywords=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "log",
        "data",
        "multithread",
    ],
    python_requires=">=3.6",
    install_requires=[
        "numpy>=1.15,<3.0",
        "dvg-debug-functions~=2.5",
        "qtpy",
    ],
    extras_require={},
)
