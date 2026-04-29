from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

OUTPUT_FILE = Path("data/phase1/user_input/latest_preferences.json")

HTML_FORM = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Restaurant Input Form</title>
    <style>
      body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; }
      label { display: block; margin-top: 12px; font-weight: bold; }
      input, select { width: 100%; padding: 8px; margin-top: 6px; }
      button { margin-top: 16px; padding: 10px 14px; }
      .hint { color: #444; font-size: 14px; margin-top: 10px; }
    </style>
  </head>
  <body>
    <h2>Basic Web UI - User Preferences</h2>
    <p class="hint">Phase 1 input source for collecting recommendation preferences.</p>
    <form method="post" action="/submit">
      <label for="location">Location</label>
      <input id="location" name="location" required>

      <label for="budget">Budget</label>
      <select id="budget" name="budget" required>
        <option value="low">low</option>
        <option value="medium">medium</option>
        <option value="high">high</option>
      </select>

      <label for="cuisine">Cuisine</label>
      <input id="cuisine" name="cuisine" required>

      <label for="minimum_rating">Minimum Rating (0 to 5)</label>
      <input id="minimum_rating" name="minimum_rating" type="number" min="0" max="5" step="0.1" required>

      <label for="optional_preferences">Additional Preferences</label>
      <input id="optional_preferences" name="optional_preferences" placeholder="family-friendly, quick service">

      <button type="submit">Save Preferences</button>
    </form>
  </body>
</html>
"""


def _save_preferences(payload: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@app.get("/")
def index():
    return render_template_string(HTML_FORM)


@app.post("/submit")
def submit():
    payload = {
        "location": request.form.get("location", "").strip(),
        "budget": request.form.get("budget", "").strip(),
        "cuisine": request.form.get("cuisine", "").strip(),
        "minimum_rating": request.form.get("minimum_rating", "").strip(),
        "optional_preferences": request.form.get("optional_preferences", "").strip(),
    }
    _save_preferences(payload)
    return jsonify(
        {
            "status": "saved",
            "message": "Preferences captured successfully.",
            "output_file": str(OUTPUT_FILE),
            "data": payload,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
