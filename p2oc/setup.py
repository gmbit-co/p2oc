from os import path
from setuptools import setup, find_packages

this_dir = path.abspath(path.dirname(__file__))
with open(path.join(this_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="p2oc",
    description="Pay to open LN channel CLI tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="0.1",
    packages=find_packages(include=("p2oc", "lnrpc")),
    include_package_data=True,
    zip_safe=True,
    python_requires=">=3.7",
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
            "grpcio-tools==1.37.*",
            "googleapis-common-protos~=1.53.0",
        ],
    },
    entry_points={"console_scripts": ["p2oc=p2oc.cli:cli"]},
)