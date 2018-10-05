import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="evfl",
    version="0.11.2",
    author="leoetlino",
    author_email="leo@leolam.fr",
    description="Library for parsing and writing Breath of the Wild Event Flow files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leoetlino/evfl",
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Topic :: Software Development :: Libraries",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires='>=3.6',
)
