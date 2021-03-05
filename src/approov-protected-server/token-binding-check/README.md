# Approov Token Binding Integration Example

This Approov integration example is from where the code example for the [Approov token binding check quickstart](/docs/APPROOV_TOKEN_BINDING_QUICKSTART.md) is extracted, and you can use it as a playground to better understand how simple and easy it is to implement [Approov](https://approov.io) in a Python FastAPI server.

## TOC - Table of Contents

* [Why?](#why)
* [How it Works?](#how-it-works)
* [Requirements](#requirements)
* [Try the Approov Integration Example](#try-the-approov-integration-example)


## Why?

To lock down your API server to your mobile app. Please read the brief summary in the [README](/README.md#why) at the root of this repo or visit our [website](https://approov.io/product.html) for more details.

[TOC](#toc---table-of-contents)


## How it works?

The Python FastAPI server is very simple and is defined in the file [src/approov-protected-server/token-check/hello-server-protected.py](src/approov-protected-server/token-check/hello-server-protected.py). Take a look at the `verifyApproovToken()` and `verifyApproovTokenBinding()` functions to see the simple code for the checks.

For more background on Approov, see the overview in the [README](/README.md#how-it-works) at the root of this repo.

[TOC](#toc---table-of-contents)


## Requirements

To run this example you will need to have installed:

* [Python 3](https://wiki.python.org/moin/BeginnersGuide/Download)
* [FastAPI](https://fastapi.tiangolo.com/tutorial/#install-fastapi)

[TOC](#toc---table-of-contents)


## Try the Approov Integration Example

First, you need to set the dummy secret in the `src/approov-protected-server/token-check/.env` file as explained [here](/README.md#the-dummy-secret).

Second, you need to install the dependencies. From the `src/approov-protected-server/token-check` folder execute:

```text
virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Now, you can run this example from the `src/approov-protected-server/token-check` folder with:

```text
uvicorn hello-server-protected:app --reload --port 8002
```
> **NOTE:** If using python from inside a docker container add the option `--host 0.0.0.0`

Finally, you can test that the Approov integration example works as expected with this [Postman collection](/README.md#testing-with-postman) or with some cURL requests [examples](/README.md#testing-with-curl).

[TOC](#toc---table-of-contents)
