# OpenSky Python Client v2.0

A comprehensive Python client library for the [OpenSky Network API](https://openskynetwork.github.io/opensky-api/) with full OAuth2 support.

## ⚠️ Breaking Change in v2.0

Version 2.0 introduces **OAuth2 Client Credentials authentication** as required by the OpenSky API. The legacy username/password authentication is no longer supported.

## Features

- **Full OAuth2 Support**: Implements the Client Credentials flow as required by OpenSky
- **Automatic Token Management**: Handles token acquisition, refresh, and expiry
- **Complete API Coverage**: All endpoints supported with proper authentication
- **Type Safety**: Full type hints and data classes
- **Rate Limiting**: Built-in rate limiting respecting API quotas
- **Error Handling**: Comprehensive error handling with custom exceptions

## Installation

```bash
pip install opensky-client

## API Endpoints

Endpoint	Method	Auth Required	Description
/states/all	GET	Optional	Get state vectors for aircraft
/flights/all	GET	Required	Get flights within time interval
/tracks/all	GET	Required*	Get track for specific aircraft
/flights/arrival	GET	Required	Get arrivals at airport
/flights/departure	GET	Required	Get departures from airport
/airports	GET	Optional	Get airport information
/states/own	GET	Required	Get state vectors from own sensors
*Historical tracks require authentication

## Setup Development Environment

### Clone repository
git clone https://github.com/yourusername/opensky-python-client.git
cd opensky-python-client

### Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

### Install dependencies
pip install -e ".[dev]"

### Install pre-commit hooks
pre-commit install