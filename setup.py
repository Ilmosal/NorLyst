# -*- coding: utf8 -*-
from setuptools import setup, find_packages

setup(
    name="NorLyst",
    version="0.3.3",
    python_requires='>3.2.0',
    author="Ilmo Salmenperä",
    author_email="ilmo.salmenpera@helsinki.fi",
    packages=find_packages(),
    include_package_data=True,
    url="http://github.com/MrCubanfrog/NorLyst",
    license="LICENSE",
    description="Simple database managing tool for analysts in ISUH(Institute of Seismology, University of Helsinki).",
    install_requires=[
        "PyQt5",
        "nordb",
        "numpy",
        "pyqtgraph",
        "obspy",
        "pathlib",
        "scipy",
        "matplotlib",
        "waveformlocator",
    ],
    long_description=open("README.md").read(),
    entry_points='''
        [console_scripts]
        norlyst=norlyst.norlyst:cli
    ''',
)
