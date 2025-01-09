#!/usr/bin/env python
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="samil",
    version="2.3",
    author="Maarten Visscher",
    author_email="mail@maartenvisscher.nl",
    description="Samil Power inverter tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mhvis/solar",
    packages=["samil"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    entry_points={
        "console_scripts": [
            "samil = samil.cli:cli"
        ]
    },
    install_requires=[
        "paho-mqtt>=1.5.0,<2",
        "click>=7.1.2,<9",
        "influxdb-client>=1.32.0,<2",
    ]
)
