from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import base64

# @link https://github.com/jpadilla/pyjwt/
import jwt

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

# @link https://approov.io/docs/latest/approov-usage-documentation/#backend-integration
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


@app.get("/")
async def root():
    return {"message": "Hello World"}
