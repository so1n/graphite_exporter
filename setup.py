import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="graphite_exporter",
    version="1.1.0",
    author="so1n",
    author_email="so1n897046026@example.com",
    description="Prometheus Graphite Exporter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/so1n/graphite_exporter",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
