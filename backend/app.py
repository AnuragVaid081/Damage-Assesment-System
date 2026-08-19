"""
Damage Assessment System — Flask Backend
=========================================
Serves the frontend templates with proper inter-page navigation,
sample assessment data, form handling, and file uploads.

Routes:
    /                       → Home page
    /new-assessment         → New assessment form
    /new-assessment (POST)  → Submit assessment (redirects to results)
    /history                → Assessment history list
    /results/<id>           → Single assessment results
    /settings               → System settings page
    /settings (POST)        → Save settings (redirects back)
"""

import os
import uuid
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.secret_key = "damage-assessment-dev-key-change-in-production"

# Upload folder for vehicle images
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# ---------------------------------------------------------------------------
# In-Memory Data Store (replaces a database for demo purposes)
# ---------------------------------------------------------------------------

# Application settings (persisted in-memory for the session)
app_settings = {
    "model_version": "v2.4",
    "threshold": 85,
    "dark_mode": False,
}

# Sample assessment records
SAMPLE_ASSESSMENTS = [
    {
        "id": "DA-2023-8941",
        "vehicle": "2022 BMW 3 Series",
        "vin": "WBA5R1C51N12XXXXX",
        "make": "BMW",
        "model": "3 Series",
        "year": 2022,
        "date": "Oct 24, 2023",
        "status": "Completed",
        "damage_count": 3,
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuBJYMLpikVqSNJtUblyqzliOW125XHLond3tqvBQ16uvyDs_jNiVZGEPHe1bYwwGTZAzp0PyRLqWJWQcmq4JGUmi7O5EgdDuaDC_DaNTkqwt9gYlMdAJA3ZAwJrbFiVIZiVgfzueZ3r5ZQDU96DtjqxFYwCLcWZHlDwC8SRJYliZM46wXtNveukX-sQxo65vLjLk1i1WpVJWYl8vxtozVwiJ4n3-LtS0iyEfsLqh3Ll4pA7DPiI15lc",
        "main_image": "https://lh3.googleusercontent.com/aida-public/AB6AXuDLeKbywxvsphc6r9nEgn1kfp1va0mADX780HGGS2kDhKubf6C1NQj1S-7Iy6rZeTEaxa-iQOC1v_eQbwme9s13pFMu69Qqf2K6agh-H90J7KxhfyahE8X7yN5v0zkMPYnL92ZmGJCM1eC5bmpqxe0T0y_Rn6G6cxucDrnRz4o17Z1yL8DLvbiz-XaMGumr0RrUb2Z-D2I5RmSfg3o0rQRb2ZJcFA7B4zhv-4oArtkQX8z_l8lsD8eM",
        "ai_summary": (
            "Computer vision analysis indicates a high-velocity impact to the rear "
            "passenger side. Primary structural deformation is observed on the rear "
            "bumper cover and the adjacent quarter panel. Paint transfer and deep "
            "striations suggest contact with a stationary object. The underlying crash "
            "bar and energy absorbers require physical inspection as secondary damage "
            "is highly probable (Confidence: 89%). No glass breakage detected."
        ),
        "anomalies": [
            {
                "part": "Rear Bumper",
                "confidence": 94,
                "damage_type": "Severe Dent / Rupture",
                "severity": "High",
                "severity_bg": "#ffdad6",
                "severity_color": "#93000a",
                "action": "Replace",
                "color": "#ba1a1a",
                "bbox": {"top": "30%", "left": "60%", "width": "25%", "height": "40%"},
            },
            {
                "part": "Quarter Panel (Pass.)",
                "confidence": 82,
                "damage_type": "Scrape / Paint Transfer",
                "severity": "Medium",
                "severity_bg": "#ffede6",
                "severity_color": "#bc4800",
                "action": "Repair & Paint",
                "color": "#bc4800",
                "bbox": {"top": "60%", "left": "45%", "width": "15%", "height": "20%"},
            },
            {
                "part": "Tail Light Assembly",
                "confidence": 99,
                "damage_type": "N/A",
                "severity": "None",
                "severity_bg": "",
                "severity_color": "",
                "action": "No action required",
                "color": "#22c55e",
                "bbox": None,
            },
        ],
    },
    {
        "id": "DA-2023-8940",
        "vehicle": "2020 Honda Civic",
        "vin": "2HGFC2F57LHXXXXX",
        "make": "Honda",
        "model": "Civic",
        "year": 2020,
        "date": "Oct 22, 2023",
        "status": "Review Required",
        "damage_count": 1,
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuAEPSFiWnkg8DH0sq3dEDkV3TppFClvJCSwEXDgIrheAa-Ln98lzdwReBrkHZydebgaCMpxncP6HegJ_UGEkV8YYFiqykPiVuwcQ2ZTtO2pdAcD6ZdBaDiqMpPDJ2iBVrouPU2gPc9RH57qf9Fe1LDAX9LrhSHUVOggnCI2GfLD12H4dhpnhZzze4vZXdAhp0WX5AHq1FwFlxvDpOlZH3YrqxAoKU1gjij2jqM5se3Nx3-6lhDpL2E1",
        "main_image": "https://lh3.googleusercontent.com/aida-public/AB6AXuAEPSFiWnkg8DH0sq3dEDkV3TppFClvJCSwEXDgIrheAa-Ln98lzdwReBrkHZydebgaCMpxncP6HegJ_UGEkV8YYFiqykPiVuwcQ2ZTtO2pdAcD6ZdBaDiqMpPDJ2iBVrouPU2gPc9RH57qf9Fe1LDAX9LrhSHUVOggnCI2GfLD12H4dhpnhZzze4vZXdAhp0WX5AHq1FwFlxvDpOlZH3YrqxAoKU1gjij2jqM5se3Nx3-6lhDpL2E1",
        "ai_summary": (
            "Analysis detects a significant dent on the driver-side door panel "
            "consistent with a side-impact collision. Paint deformation and creasing "
            "visible across a 30cm span. Door alignment may be compromised — "
            "recommend physical hinge inspection. No window damage detected."
        ),
        "anomalies": [
            {
                "part": "Driver Side Door",
                "confidence": 88,
                "damage_type": "Deep Dent",
                "severity": "High",
                "severity_bg": "#ffdad6",
                "severity_color": "#93000a",
                "action": "Replace Panel",
                "color": "#ba1a1a",
                "bbox": {"top": "35%", "left": "30%", "width": "30%", "height": "35%"},
            },
        ],
    },
    {
        "id": "DA-2023-8939",
        "vehicle": "2019 Ford F-150",
        "vin": "1FTEW1EP0KKXXXXX",
        "make": "Ford",
        "model": "F-150",
        "year": 2019,
        "date": "Oct 20, 2023",
        "status": "Completed",
        "damage_count": 0,
        "image_url": None,
        "main_image": None,
        "ai_summary": (
            "Comprehensive scan completed. No structural or cosmetic anomalies "
            "detected across all inspected panels. Vehicle appears to be in good "
            "condition. No further action recommended."
        ),
        "anomalies": [],
    },
    {
        "id": "DA-2023-8938",
        "vehicle": "2021 Toyota Camry",
        "vin": "4T1B11HK5MUXXXXX",
        "make": "Toyota",
        "model": "Camry",
        "year": 2021,
        "date": "Oct 18, 2023",
        "status": "Completed",
        "damage_count": 2,
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCzzyYIeUYuMxxC64JIfzQ05deqctrWSX7weR9sWcVi5XRLVFzPjq6uNBJuZ3iuZKkpAn6-YsvGMTy-KR3IIPf2qDSwtr4atT4BbAn4E7cNjGZFV0LMP7xIRgEpZclPG_v1wzX2oyut5xl2lZYamI5qd3Bt0nLrXH5Qa7NXzlFaN2Vd4NBts2OUmbdVRrmrVoLFU3SymjgFTtjueUQ4QU1gWMKT9rJ4EZZcdthSz5M4JoI5ODl50tjj",
        "main_image": "https://lh3.googleusercontent.com/aida-public/AB6AXuCzzyYIeUYuMxxC64JIfzQ05deqctrWSX7weR9sWcVi5XRLVFzPjq6uNBJuZ3iuZKkpAn6-YsvGMTy-KR3IIPf2qDSwtr4atT4BbAn4E7cNjGZFV0LMP7xIRgEpZclPG_v1wzX2oyut5xl2lZYamI5qd3Bt0nLrXH5Qa7NXzlFaN2Vd4NBts2OUmbdVRrmrVoLFU3SymjgFTtjueUQ4QU1gWMKT9rJ4EZZcdthSz5M4JoI5ODl50tjj",
        "ai_summary": (
            "Rear bumper shows surface-level scuff marks and minor paint abrasion. "
            "Impact force appears low — likely from a parking lot incident. Bumper "
            "structural integrity is intact. Cosmetic repair recommended. Secondary "
            "scratching detected on the trunk lid near the badge."
        ),
        "anomalies": [
            {
                "part": "Rear Bumper",
                "confidence": 91,
                "damage_type": "Scuff / Abrasion",
                "severity": "Low",
                "severity_bg": "#dbe1ff",
                "severity_color": "#003ea8",
                "action": "Buff & Polish",
                "color": "#004ac6",
                "bbox": {"top": "55%", "left": "25%", "width": "50%", "height": "25%"},
            },
            {
                "part": "Trunk Lid",
                "confidence": 76,
                "damage_type": "Light Scratch",
                "severity": "Low",
                "severity_bg": "#dbe1ff",
                "severity_color": "#003ea8",
                "action": "Touch-up Paint",
                "color": "#004ac6",
                "bbox": {"top": "30%", "left": "40%", "width": "20%", "height": "15%"},
            },
        ],
    },
]


def get_assessment_by_id(assessment_id: str) -> dict | None:
    """Look up an assessment by its ID string."""
    for a in SAMPLE_ASSESSMENTS:
        if a["id"] == assessment_id:
            return a
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    """Render the home / landing page."""
    return render_template("home.html", active_page="home")


@app.route("/new-assessment")
def new_assessment():
    """Render the new assessment upload & vehicle details form."""
    return render_template("new_assessment.html", active_page="new_assessment")


@app.route("/new-assessment", methods=["POST"])
def submit_assessment():
    """
    Handle new assessment form submission.
    Saves uploaded images (if any), creates a new assessment record,
    and redirects to the results page.
    """
    # Collect form data
    make = request.form.get("make", "Unknown")
    model = request.form.get("model", "Unknown")
    year = request.form.get("year", "N/A")
    vin = request.form.get("vin", "N/A")

    # Generate a new assessment ID
    new_id = f"DA-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"

    # Handle file uploads
    uploaded_files = request.files.getlist("images")
    saved_image_url = None
    for f in uploaded_files:
        if f and f.filename:
            safe_name = f"{new_id}_{f.filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
            f.save(save_path)
            if saved_image_url is None:
                saved_image_url = f"/static/uploads/{safe_name}"

    # Create a new assessment record (simulating AI analysis)
    new_assessment_record = {
        "id": new_id,
        "vehicle": f"{year} {make} {model}",
        "vin": vin if vin else "N/A",
        "make": make,
        "model": model,
        "year": year,
        "date": datetime.now().strftime("%b %d, %Y"),
        "status": "Completed",
        "damage_count": 2,
        "image_url": saved_image_url,
        "main_image": saved_image_url,
        "ai_summary": (
            f"AI analysis of the {year} {make} {model} is complete. "
            "The system has detected potential damage areas that require "
            "further review. Please inspect the highlighted regions for "
            "structural and cosmetic anomalies. Overall assessment confidence "
            "is 87%."
        ),
        "anomalies": [
            {
                "part": "Front Bumper",
                "confidence": 87,
                "damage_type": "Dent / Deformation",
                "severity": "Medium",
                "severity_bg": "#ffede6",
                "severity_color": "#bc4800",
                "action": "Repair",
                "color": "#bc4800",
                "bbox": {"top": "40%", "left": "20%", "width": "30%", "height": "30%"},
            },
            {
                "part": "Hood Panel",
                "confidence": 72,
                "damage_type": "Scratch / Paint Loss",
                "severity": "Low",
                "severity_bg": "#dbe1ff",
                "severity_color": "#003ea8",
                "action": "Touch-up Paint",
                "color": "#004ac6",
                "bbox": {"top": "15%", "left": "35%", "width": "25%", "height": "20%"},
            },
        ],
    }

    # Prepend to the list so it appears first in history
    SAMPLE_ASSESSMENTS.insert(0, new_assessment_record)

    flash(f"Assessment {new_id} created successfully!", "success")
    return redirect(url_for("assessment_results", assessment_id=new_id))


@app.route("/history")
def assessment_history():
    """Render the assessment history page with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = 4
    total = len(SAMPLE_ASSESSMENTS)
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Clamp page number
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_assessments = SAMPLE_ASSESSMENTS[start:end]

    return render_template(
        "assessment_history.html",
        active_page="history",
        assessments=page_assessments,
        page=page,
        total_pages=total_pages,
    )


@app.route("/results/<assessment_id>")
def assessment_results(assessment_id: str):
    """Render the assessment results page for a specific assessment."""
    assessment = get_assessment_by_id(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment_history"))

    return render_template(
        "assessment_results.html",
        active_page="new_assessment",  # Results is contextually under "New Assessment"
        assessment=assessment,
    )


@app.route("/settings")
def settings():
    """Render the system settings page."""
    return render_template(
        "settings.html",
        active_page="settings",
        settings=app_settings,
    )


@app.route("/settings", methods=["POST"])
def save_settings():
    """Handle saving system settings from the form."""
    app_settings["model_version"] = request.form.get("model_version", "v2.4")
    app_settings["threshold"] = int(request.form.get("threshold", 85))
    app_settings["dark_mode"] = "dark_mode" in request.form

    flash("Settings saved successfully!", "success")
    return redirect(url_for("settings"))


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Damage Assessment System — Backend Server")
    print("=" * 60)
    print(f"  Home:            http://127.0.0.1:5000/")
    print(f"  New Assessment:  http://127.0.0.1:5000/new-assessment")
    print(f"  History:         http://127.0.0.1:5000/history")
    print(f"  Settings:        http://127.0.0.1:5000/settings")
    print("=" * 60 + "\n")

    app.run(debug=True, host="127.0.0.1", port=5000)
