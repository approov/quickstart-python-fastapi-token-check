from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# @link https://github.com/jpadilla/pyjwt/
import jwt
import base64
import hashlib

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

# @link https://approov.io/docs/latest/approov-usage-documentation/#token-binding
# @IMPORTANT FastAPI seems to execute middleware in the reverse order they
#            appear in the code, therefore this one must come right before the
#            verifyApproovToken() middleware.
@app.middleware("http")
async def verifyApproovTokenBinding(request: Request, call_next):
    # Note that the `pay` claim will, under normal circumstances, be present,
    # but if the Approov failover system is enabled, then no claim will be
    # present, and in this case you want to return true, otherwise you will not
    # be able to benefit from the redundancy afforded by the failover system.
    if not 'pay' in request.state.approov_token_claims:
        # You may want to add some logging here.
        return JSONResponse({}, status_code = 401)

    # We use the Authorization token, but feel free to use another header in
    # the request. Beqar in mind that it needs to be the same header used in the
    # mobile app to qbind the request with the Approov token.
    token_binding_header = request.headers.get("Authorization")

    if not token_binding_header:
        # You may want to add some logging here.
        return JSONResponse({}, status_code = 401)

    # We need to hash and base64 encode the token binding header, because that's
    # how it was included in the Approov token on the mobile app.
    token_binding_header_hash = hashlib.sha256(token_binding_header.encode('utf-8')).digest()
    token_binding_header_encoded = base64.b64encode(token_binding_header_hash).decode('utf-8')

    if request.state.approov_token_claims['pay'] == token_binding_header_encoded:
        return await call_next(request)

    return JSONResponse({}, status_code = 401)

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
        request.state.approov_token_claims = jwt.decode(approov_token, APPROOV_SECRET, algorithms=['HS256'])
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
