#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  22 13:45:04 2020
@author: Ahmed Qamesh
"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="CANMOPSWrapper",
    version="1.2.0",
    author="Ahmed Qamesh",
    author_email="ahmed.qamesh@cern.ch",
    description="A CAN wrappper for MOPS messages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=['coloredlogs', 'verboselogs', 'aenum'],    
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)