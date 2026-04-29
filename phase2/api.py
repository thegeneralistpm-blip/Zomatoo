from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, request

from phase2.normalize_validate import ValidationError, validate_and_standardize

app = Flask(__name__)


@app.post("/phase2/standardize")
def standardize_preferences():
    payload = request.get_json(silent=True) or {}
    try:
        standardized = validate_and_standardize(payload)
    except ValidationError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    return jsonify({"status": "ok", "data": asdict(standardized)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
