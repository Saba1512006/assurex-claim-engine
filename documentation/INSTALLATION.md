# Installation & execution (SRS deliverables 9–10)

## Prerequisites

| Item | Requirement |
|---|---|
| Operating system | Windows 10/11, macOS 12+, Ubuntu 20.04+ (any OS with Python) |
| Python | 3.10, 3.11 or 3.12 (3.11 recommended; `scikit-learn==1.9.1` is pinned so the saved model loads) |
| Git | any recent version |
| Optional | Tesseract OCR (reads *image* receipts); Chromium via Playwright (only to re-render report diagrams) |

## Setup

```bash
git clone https://github.com/Saba1512006/assurex-claim-engine.git
cd assurex-claim-engine
python -m venv venv
# Windows (PowerShell): .\venv\Scripts\Activate.ps1      macOS/Linux: source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Environment variables

`python database/seed.py` creates a `.env` file with a random `SECRET_KEY` the first time it runs. You can
also set these yourself (in `.env` or the environment):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | *(required)* | Signs sessions and CSRF tokens. The app refuses to start without it. |
| `DATABASE_URL` | `sqlite:///database/assurex.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `UPLOAD_DIR` | `data/uploads` | Where documents and Claim Summary Cards are stored |
| `WARRANTY_EXPIRY_ALERT_DAYS` | `30` | Initial alert window (admins change it in the app) |
| `RATELIMIT_STORAGE_URI` | `memory://` | Use `redis://…` when running several workers |
| `FLASK_DEBUG` | `0` | `1` for the debug server |

## Database

```bash
python database/seed.py              # drop + recreate tables, add demo users, products and 12 evaluated claims
python database/seed.py --if-empty   # only seed an empty database (used on deploy)
```

Tables are created from the SQLAlchemy models (`src/models/entities.py`). The seed prints the status mix
it produced. The **default administrator** is `admin@assurex.local` / `AdminPass123!` — change the
password from *Profile* after the first sign-in on any shared deployment, and invite real users from
*Access*.

## Models

| Model | Location | How it gets there |
|---|---|---|
| Python classification model | `model/python_model/claim_classifier_v2.joblib` + `model_card_v2.json` | Included. Rebuild with `python notebooks/train_python_v2.py` |
| Google Teachable Machine | `model/teachable_machine/model_unquant.tflite` + `labels.txt` | Train in the browser on `data/summary_cards/train/`, export *Tensorflow Lite → Floating point*, then upload in Admin › Models (or copy the two files into the folder). Run the evaluation afterwards. |

`labels.txt` may use the canonical names (`0 Valid Claim`) or the folder names (`0 valid`, `2 manual_review`).

## OCR

PDF receipts with a text layer are read by `pdfplumber` (installed from requirements). To read photos
and scans, install Tesseract:

* Windows: install from the UB Mannheim build, keep the default path `C:\Program Files\Tesseract-OCR\`, and add it to `PATH`.
* macOS: `brew install tesseract` · Ubuntu/Debian: `sudo apt install tesseract-ocr`

Without Tesseract, image receipts are still accepted and the user types the details (the app says so).

## Run

```bash
python src/app.py                     # development server: http://127.0.0.1:5000
gunicorn wsgi:app --workers 2         # production (Linux/macOS)
python -m pytest -q                   # 197 automated tests
```

PythonAnywhere: point the WSGI file at the project and `from wsgi import application`; set `SECRET_KEY`
in the WSGI file or a `.env`, then run `python database/seed.py --if-empty` once in a console.
Render: `render.yaml` builds, seeds an empty database and generates `SECRET_KEY` automatically.

## Folder setup

Everything needed is in the repository. Created at runtime: `data/uploads/` (documents, cards),
`database/assurex.db`, `.env`. None of them are committed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RuntimeError: SECRET_KEY is not set` | Run `python database/seed.py` once, or set `SECRET_KEY` |
| Sign-in works but you're immediately signed out (local http) | Use `python src/app.py` (it disables the secure-cookie flag for http). Behind https nothing needs changing. |
| “Python model could not be loaded” | Install the pinned `scikit-learn==1.9.1`, or retrain with `python notebooks/train_python_v2.py` |
| Every claim ends in Manual Review | The Teachable Machine model isn't installed yet (Admin › Models shows the status) |
| “No TensorFlow Lite runtime installed” | `pip install ai-edge-litert` (or `tflite-runtime` / `tensorflow`) |
| Receipt photo: “no text found” | Install Tesseract or upload a PDF; you can also enter the details by hand |
| `sqlite3.OperationalError: no such column` after pulling | The schema changed: `python database/seed.py` (demo) or migrate your data (see `src/security/MIGRATION.md`) |
| “This form expired” | The CSRF token is tied to your session — reload the page and submit again |
| Too many attempts / account locked | Wait 15 minutes, or an admin uses *Sign out* on the Access page to clear the lock |
