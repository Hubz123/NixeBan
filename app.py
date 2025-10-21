from __future__ import annotations
import os
import time
import logging
from flask import Flask, jsonify

log = logging.getLogger(__name__)
app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return jsonify(status="ok", ts=int(time.time())), 200

@app.get("/")
def index():
    return "NIXE web is up", 200
