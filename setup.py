from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="TempBox",
    version="0.1.0",
    author="D Perez",
    author_email="",
    description="A Python wrapper for the 1secmail temporary email service.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Davis-3450/TempBox",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
