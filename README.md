# Approov QuickStart - Python FastAPI Token Check

[Approov](https://approov.io) is an API security solution used to verify that requests received by your backend services originate from trusted versions of your mobile apps.

This repo implements the Approov server-side request verification code with the Python FastAPI framework, which performs the verification check before allowing valid traffic to be processed by the API endpoint.


## Approov Integration Quickstart

The quickstart was tested with the following Operating Systems:

* Ubuntu 20.04
* MacOS Big Sur
* Windows 10 WSL2 - Ubuntu 20.04

First, setup the [Appoov CLI](https://approov.io/docs/latest/approov-installation/index.html#initializing-the-approov-cli).

Now, register the API domain for which Approov will issues tokens:

```bash
approov api -add api.example.com
```

Next, enable your Approov `admin` role with:

```bash
eval `approov role admin`
```

Now, get your Approov Secret with the [Appoov CLI](https://approov.io/docs/latest/approov-installation/index.html#initializing-the-approov-cli):

```bash
approov secret -get base64
```

Next, add the [Approov secret](https://approov.io/docs/latest/approov-usage-documentation/#account-secret-key-export) to your project `.env` file:

```env
APPROOV_BASE64_SECRET=approov_base64_secret_here
```

Now, add to your `requirements.txt` file the [JWT dependency](https://github.com/jpadilla/pyjwt/):

```bash
PyJWT==1.7.1 # update the version to the latest one
```

Next, you need to install the dependencies:

```bash
pip3 install -r requirements.txt
```

Now, add this code to your project, just before your first API endpoint:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# @link https://github.com/jpadilla/pyjwt/
import jwt
import base64

# @link https://github.com/theskumar/python-dotenv
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
from os import getenv

# Token secret value obtained with the Approov CLI tool:
#  - approov secret -get
approov_base64_secret = getenv('APPROOV_BASE64_SECRET')

if approov_base64_secret == None:
    raise ValueError("Missing the value for environment variable: APPROOV_BASE64_SECRET")

APPROOV_SECRET = base64.b64decode(approov_base64_secret)

app = FastAPI()

################################################################################
# ONLY ADD YOUR MIDDLEWARE BEFORE THIS LINE.
# - FastAPI seems to execute middleware in the reverse we declare it in the
#   code.
# - Approov middleware SHOULD be the first to be executed in the request life
#   cycle.
################################################################################

# @link https://approov.io/docs/latest/approov-usage-documentation/#backend-integration
# @IMPORTANT FastAPI seems to execute middleware in the reverse order they
#            appear in the code, therefore this one must come as the LAST of the
#            middleware's.
@app.middleware("http")
async def verifyApproovToken(request: Request, call_next):
    approov_token = request.headers.get("Approov-Token")

    # If we didn't find a token, then reject the request.
    if approov_token == "":
        # You may want to add some logging here.
        # return None
        return JSONResponse({}, status_code = 401)

    try:
        # Decode the Approov token explicitly with the HS256 algorithm to avoid
        # the algorithm None attack.
        approov_token_claims = jwt.decode(approov_token, APPROOV_SECRET, algorithms=['HS256'])
        return await call_next(request)
    except jwt.ExpiredSignatureError as e:
        # You may want to add some logging here.
        return JSONResponse({}, status_code = 401)
    except jwt.InvalidTokenError as e:
        # You may want to add some logging here.
        return JSONResponse({}, status_code = 401)

# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
```

> **NOTE:** When the Approov token validation fails we return a `401` with an empty body, because we don't want to give clues to an attacker about the reason the request failed, and you can go even further by returning a `400`.

Using the middleware approach will ensure that all endpoints in your API will be protected by Approov.

Not enough details in the bare bones quickstart? No worries, check the [detailed quickstarts](QUICKSTARTS.md) that contain a more comprehensive set of instructions, including how to test the Approov integration.


## More Information

* [Approov Overview](OVERVIEW.md)
* [Detailed Quickstarts](QUICKSTARTS.md)
* [Examples](EXAMPLES.md)
* [Testing](TESTING.md)

### System Clock

In order to correctly check for the expiration times of the Approov tokens is very important that the backend server is synchronizing automatically the system clock over the network with an authoritative time source. In Linux this is usually done with a NTP server.


## Issues

If you find any issue while following our instructions then just report it [here](https://github.com/approov/quickstart-python-fastapi-token-check/issues), with the steps to reproduce it, and we will sort it out and/or guide you to the correct path.


## Useful Links

If you wish to explore the Approov solution in more depth, then why not try one of the following links as a jumping off point:

* [Approov Free Trial](https://approov.io/signup)(no credit card needed)
* [Approov Get Started](https://approov.io/product/demo)
* [Approov QuickStarts](https://approov.io/docs/latest/approov-integration-examples/)
* [Approov Docs](https://approov.io/docs)
* [Approov Blog](https://approov.io/blog/)
* [Approov Resources](https://approov.io/resource/)
* [Approov Customer Stories](https://approov.io/customer)
* [Approov Support](https://approov.zendesk.com/hc/en-gb/requests/new)
* [About Us](https://approov.io/company)
* [Contact Us](https://approov.io/contact)
