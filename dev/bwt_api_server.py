#!/usr/bin/env python3
"""Simple dev server to mock BWT APIs (Perla, Silk, SmartDos).

Usage: python dev/bwt_api_server.py --mode perla
JSON files are read from `dev/data/<mode>/`.
Perla endpoints: GET /api/<EndpointName> (e.g. /api/GetCurrentData)
Silk endpoint: GET /silk/registers
SmartDos endpoints: GET /api/v1/gatt/<uuid>
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

from flask import Flask, jsonify, abort, request

_LOGGER = logging.getLogger(__name__)
app = Flask(__name__)


def load_json_files(folder: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if not folder.exists():
        _LOGGER.warning("Data folder %s does not exist", folder)
        return data
    for p in folder.glob("*.json"):
        try:
            with p.open("r", encoding="utf-8") as fh:
                data[p.stem] = json.load(fh)
        except Exception as exc:  # pragma: no cover - dev script
            _LOGGER.exception("Failed to load %s: %s", p, exc)
    return data

def _require_perla_auth() -> bool:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False

    token = auth_header.removeprefix("Basic ").strip()
    try:
        decoded = base64.b64decode(token).decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return False

    return decoded == "user:perla"


@app.route("/api")
def perla_root():
    if app.config.get("mode") != "perla":
        abort(404)

    if not _require_perla_auth():
        return "Not Found", 404

    return "Not Found", 404


@app.route("/api/<path:endpoint>")
def perla_api(endpoint: str):
    # endpoint will be like GetCurrentData or GetDailyData
    if app.config.get("mode") != "perla":
        abort(404)
    if not _require_perla_auth():
        return "Not Found", 404

    data = app.config.get("data", {})
    key = endpoint
    if key in data:
        return jsonify(data[key])
    abort(404)


@app.route("/silk/registers")
def silk_registers():
    if app.config.get("mode") != "silk":
        abort(404)
    data = app.config.get("data", {})
    # expect file named registers.json -> key 'registers'
    if "registers" in data:
        return jsonify(data["registers"])  # should be a dict with params
    # also accept file named params.json
    if "params" in data:
        return jsonify(data["params"])  # directly return params
    abort(404)


@app.route("/api/v1/gatt/<uuid>")
def smartdos_gatt(uuid: str):
    if app.config.get("mode") != "smartdos":
        abort(404)
    data = app.config.get("data", {})
    key = f"gatt_{uuid}"
    if key in data:
        return jsonify(data[key])
    abort(404)


@app.route("/")
def index():
    mode = app.config.get("mode")
    available = list(app.config.get("data", {}).keys())
    return jsonify({"mode": mode, "available": available})


def main() -> None:  # pragma: no cover - run as script
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("perla", "silk", "smartdos"), required=True)
    parser.add_argument("--data-dir", default="dev/data")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    data_folder = Path(args.data_dir) / args.mode
    data = load_json_files(data_folder)

    app.config["mode"] = args.mode
    app.config["data"] = data

    # default ports: perla -> 8080, silk/smartdos -> 80
    if args.port:
        port = args.port
    else:
        port = 8080 if args.mode == "perla" else 80

    _LOGGER.info("Starting mock BWT %s server on %s:%s", args.mode, args.host, port)
    app.run(host=args.host, port=port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
