#!/usr/bin/env python
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="samil",
    version="2.1.0a5",
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
    # * 3.4 is required for paho-mqtt:tls_set()
    # * 3.5 is required for socket.socketpair() in Windows, only used for test cases
    # * 3.5 is required for socket.listen() optional backlog parameter
    # * CI only tests >=3.5
    python_requires='>=3.5',
    entry_points={
        "console_scripts": [
            "samil = samil.cli:cli"
        ]
    },
    install_requires=[
        "paho-mqtt>=1.5.0",
        "click>=7.1.2",
    ]
)
