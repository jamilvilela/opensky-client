from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(os.path.join("opensky", "__init__.py"), "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "2.0.0"

setup(
    name="opensky-client",
    version=version,
    author="Jamil Miranda Vilela",
    author_email="jamilvilela@gmail.com",
    description="A Python client library for the OpenSky Network API with OAuth2 authentication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jamilvilela/opensky-client",
    project_urls={
        "Bug Tracker": "https://github.com/jamilvilela/opensky-client/issues",
        "Documentation": "https://github.com/jamilvilela/opensky-client/wiki",
        "Source Code": "https://github.com/jamilvilela/opensky-client",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "pytz>=2021.1",
        "python-dotenv>=0.19.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.12",
            "black>=21.5b2",
            "isort>=5.9",
            "mypy>=0.910",
            "flake8>=3.9",
            "pre-commit>=2.13",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5.2",
        ],
        "examples": [
            "matplotlib>=3.4",
            "geopandas>=0.9",
            "folium>=0.12",
            "python-dotenv>=0.19.0",
        ],
    },
    keywords=[
        "opensky",
        "ads-b",
        "aviation",
        "flight-tracking",
        "api-client",
        "air-traffic",
        "oauth2",
    ],
)