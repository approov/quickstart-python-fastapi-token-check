# Unprotected Server Example

The unprotected example is the base reference to build the [Approov protected servers](/src/approov-protected-server/). This a very basic Hello World server.


## TOC - Table of Contents

* [Why?](#why)
* [How it Works?](#how-it-works)
* [Requirements](#requirements)
* [Try It](#try-it)


## Why?

To be the starting building block for the [Approov protected servers](/src/approov-protected-server/), that will show you how to lock down your API server to your mobile app. Please read the brief summary in the [README](/README.md#why) at the root of this repo or visit our [website](https://approov.io/product.html) for more details.

[TOC](#toc---table-of-contents)


## How it works?

The Python FastAPI server is very simple and is defined in the file [src/unprotected-server/hello-server-unprotected.py](/src/unprotected-server/hello-server-unprotected.py).

The server only replies to the endpoint `/` with the message:

```json
{"message": "Hello, World!"}
```

[TOC](#toc---table-of-contents)


## Requirements

To run this example you will need to have installed:

* [Python 3](https://wiki.python.org/moin/BeginnersGuide/Download)
* [FastAPI](https://fastapi.tiangolo.com/tutorial/#install-fastapi)

[TOC](#toc---table-of-contents)


## Try It

First install the dependencies. From the `src/unprotected-server` folder execute:

```text
virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Now, you can run this example from the `src/unprotected-server` folder with:

```text
uvicorn hello-server-unprotected:app --reload --port 8002
```
> **NOTE:** If using python from inside a docker container add the option `--host 0.0.0.0`

Finally, you can test that it works with:

```text
curl -iX GET 'http://localhost:8002'
```

The response will be:

```text
HTTP/1.1 200 OK
date: Fri, 05 Mar 2021 16:51:01 GMT
server: uvicorn
content-length: 25
content-type: application/json

{"message":"Hello World"}
```

[TOC](#toc---table-of-contents)
