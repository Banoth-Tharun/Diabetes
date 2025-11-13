# Diabetes Management Flask App

A local-first Flask web application for diabetes risk classification, glucose forecasting, and explainability with dual dashboards for patients and clinicians.

## Features

- Risk classification from PIMA-style inputs (pregnancies, glucose, BMI, blood pressure, age, etc.).
- Glucose forecasting from uploaded CGM CSV or manual readings.
- Explainability via SHAP (feature contributions per prediction).
- Dual dashboards:
  - Patient: current risk, forecast chart, SHAP importance, history, alerts.
  - Clinician: patient list with risk levels, detail pages, alerts, export CSV/PDF.
- Offline-friendly: runs locally without Docker, caches recent predictions in SQLite.
- Privacy-preserving: placeholder code for federated learning simulation using Flower.
- Authentication with role-based access (patient vs clinician).

## Project Structure

```
.
├── app.py
├── models.py
├── ml/
│   ├── model.py
│   ├── train_model.py
│   ├── explain.py
│   └── forecast.py
├── data/
│   └── pima_sample.csv
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── patient_dashboard.html
│   └── clinician_dashboard.html
├── static/
│   ├── css/styles.css
│   └── js/app.js
├── tests/
│   └── test_api.py
├── federated_sim.py
├── requirements.txt
└── README.md
```

## Setup

1) Create and activate a virtual environment

Windows PowerShell:
```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3) Train the ML model
```bash
python ml/train_model.py --data data/pima_sample.csv --out ml/model.pkl
```

4) Initialize the database and run the app
```bash
python app.py
```
Then open `http://127.0.0.1:5000` in your browser.

Default users (seeded on first run):
- Clinician: `clinician@example.com` / `password123`
- Patient: `patient@example.com` / `password123`

## API Endpoints

- POST `/api/predict` – JSON body with PIMA-style features; returns risk and probability.
- POST `/api/explain` – same input; returns SHAP-like values per feature.
- POST `/api/forecast` – JSON `readings` or CSV upload; returns 60-min forecast.

## Tests

```bash
pytest -q
```

## Federated Learning (Optional)

```bash
python federated_sim.py --rounds 1
```

## Future Improvements

- PWA conversion for offline UI and caching
- Wearable integrations and FHIR export
- Advanced forecasting with uncertainty bands
- Email/SMS alerts




