from os import path
from setuptools import setup, find_packages

this_dir = path.abspath(path.dirname(__file__))
with open(path.join(this_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="p2oc",
    version="0.2",
    author="Julian Villella",
    author_email="jvillella.jv@gmail.com",
    description='p2oc allows a node to request an inbound Lightning Network channel in exchange for an off-chain fee.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/flywheelstudio/p2oc",
    project_urls={
        "Bug Tracker": "https://github.com/flywheelstudio/p2oc/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=("p2oc", "lnrpc")),
    zip_safe=True,
    python_requires=">=3.6",
    install_requires=[
        "grpcio~=1.37.0",
        "click~=7.1.0",
        "python-bitcoinlib~=0.11.0",
        "python-bitcointx~=1.1.0",
    ],
    extras_require={
        "dev": [
            "pytest~=6.2.0",
            "black~=21.5b0",
            "pylint~=2.8.2",
            "grpcio-tools~=1.37.0",
            "googleapis-common-protos~=1.53.0",
        ],
    },
    entry_points={"console_scripts": ["p2oc=p2oc.cli:cli"]},
)
