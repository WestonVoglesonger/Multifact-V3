"""Entrypoint of backend API exposing the FastAPI `app` to be served by an application server such as uvicorn."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from .api.test_api import api as test_api
from .api.debug_routes import api as debug_api
__authors__ = ["Weston Voglesonger"]
__copyright__ = "Copyright 2023"
__license__ = "MIT"

description = """
Welcome to the Edge Carolina RESTful Application Programming Interface.
"""

# Metadata to improve the usefulness of OpenAPI Docs /docs API Explorer
app = FastAPI(
    title="Edge Carolina API",
    version="0.0.1",
    description=description,
    openapi_tags=[]
)

# Use GZip middleware for compressing HTML responses over the network
app.add_middleware(GZipMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1460"],  # or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Plugging in each of the router APIs
feature_apis = [
    test_api,
    debug_api,
]

for feature_api in feature_apis:
    app.include_router(feature_api)
