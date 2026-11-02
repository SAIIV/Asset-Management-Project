# Circular Campus: Intelligent Campus Resource Exchange

COSC 336 - Introduction to Software Engineering, Fall 2026, Group 6

## Project overview

Circular Campus is a web application that helps university departments reuse
assets instead of buying new ones. Departments register surplus assets, other
departments request what they need, an approver signs off, and the asset is
transferred. The system tracks each asset's life cycle (maintenance, donation,
recycling, disposal) and reports the money, waste and CO2e saved. AI features
suggest categories, rank matching assets and draft report summaries; a person
always confirms each AI suggestion.

The full design is in [docs/phase-4-5/](docs/phase-4-5/) and the Phase 6 plan
(features and owners) is in [docs/phase-6/](docs/phase-6/).

## Technology

| Part | Choice |
|---|---|
| Language | Python 3.12 |
| Web framework | Django 5.2 (LTS), server-rendered templates |
| Database | PostgreSQL 16 with the pgvector extension, run in Docker (`docker-compose.yml`) |
| Secrets | `.env` file, never committed (see `.env.example`) |

## Repository structure

```text
circular_campus/   Project settings and top-level URLs
accounts/          Accounts & Administration: users, roles, audit log      (Ali)
assets/            Assets & Catalogue: departments, categories, assets    (Saeed)
exchange/          Search & Requests: requests, match recommendations     (Abdullah, Ali)
transfers/         Reservations, approvals and transfers                  (Humaid)
reports/           Sustainability dashboard, reports, CSV export          (Saeed, Abdullah)
notifications/     In-app notifications                                   (Abdullah)
ai/                AI gateway, AI services and AI records                 (Humaid, Ali)
docs/              Phase reports, design document and meeting notes
templates/         Shared page layout (base.html)
static/css/        The one shared stylesheet (circular.css)
docker-compose.yml PostgreSQL 16 + pgvector database for local development
requirements.txt   Python packages, same versions for everyone
.env.example       Template for your local .env file (no real keys)
```

Each folder under the project root is one Django app and matches one module of
the architecture view in the design document.

## Setup for team members (Windows, VS Code)

You need: Python 3.12, Git, Docker Desktop and VS Code.

1. Clone the repository and open the folder in VS Code.
2. Create and activate a virtual environment, then install the packages:

   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   If PowerShell blocks `Activate.ps1`, run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

3. Create your own `.env` from the template and put a secret key in it:

   ```powershell
   copy .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   Paste the printed key after `DJANGO_SECRET_KEY=` in `.env`.

4. Fill in the database values in `.env` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`).
   Any local password works; Docker creates the database with it.

5. Start PostgreSQL 16 + pgvector in Docker (Docker Desktop must be running):

   ```powershell
   docker compose up -d
   docker compose ps
   ```

   Expected: the `circular_campus_db` container shows `running (healthy)`.
   The data is kept in a Docker volume. `docker compose down` stops the
   database; `docker compose down -v` also deletes all data.

6. Check that Django starts, then create all tables:

   ```powershell
   python manage.py check
   python manage.py migrate
   ```

   `migrate` turns on the pgvector extension and creates the 26 tables of
   the design document (Section 9) plus Django's own tables.

7. Load the synthetic test data:

   ```powershell
   python manage.py seed_data
   ```

   This creates 8 roles, 5 fictional departments, 12 categories, 50 synthetic
   assets and 4 test users. All of it is invented and marked "Synthetic";
   no real staff or asset data is used. Running it again does not create
   duplicates.

   | Role | Email | Password |
   |---|---|---|
   | Requester | requester@circular-campus.example | Synthetic-Demo-2026 |
   | Custodian | custodian@circular-campus.example | Synthetic-Demo-2026 |
   | Approver | approver@circular-campus.example | Synthetic-Demo-2026 |
   | Administrator | admin@circular-campus.example | Synthetic-Demo-2026 |

   The Administrator can open the Django admin at http://127.0.0.1:8000/admin/
   after `python manage.py runserver`. To start again from an empty database:
   `docker compose down -v`, `docker compose up -d`, `migrate`, `seed_data`.

More setup steps are added as they land.

## Data model

All 26 tables of the Design Document, Section 9 are Django models. Table and
column names in PostgreSQL are exactly the names of the data dictionary and
Figure 63 (for example `"Asset"."estimatedValueAED"`); in Python the same
column is `asset.estimated_value_aed`. All enumerations (Condition,
AssetStatus, RequestStatus, ...) are in `circular_campus/choices.py`.

| App | Tables |
|---|---|
| accounts | User, Role, UserRole, AuditLog |
| assets | Department, Category, Asset, ITAsset, LabEquipment, FurnitureAsset, AssetCollection, AssetCollectionItem, Attachment, Inspection, MaintenanceRecord, LifecycleAction |
| exchange | ResourceRequest, RequestSpecification, MatchRecommendation |
| transfers | Reservation, Approval, Transfer |
| reports | SustainabilityImpact |
| notifications | Notification |
| ai | ModelVersion, AIRecord |

## Page layout and styles

Every page extends the shared layout in `templates/base.html` and uses the one
stylesheet `static/css/circular.css`, copied from our mockups (Design Document
Section 7). The top bar shows the signed-in user, their department and role.

```django
{% extends "base.html" %}
{% block title %}Assets - Circular Campus{% endblock %}
{% block nav_assets %}on{% endblock %}
{% block content %}
  <h1>Assets</h1>
  <div class="card">...</div>
{% endblock %}
```

Useful classes: `card`, `card ai` (every AI suggestion), `num`/`kpi`,
`tag ok|warn|bad|ai`, `btn primary|danger`, `grid` (two-column form),
`down` (AI unavailable box). Menu items: `nav_dashboard`, `nav_assets`,
`nav_requests`, `nav_matches`, `nav_transfers`, `nav_approvals`,
`nav_maintenance`, `nav_reports`, `nav_sustainability`, `nav_inbox`.

## Working rules

- Never commit to `main`. Create a branch per feature, for example
  `feature/c5-transfer`, and open a pull request; one other member reviews it.
- Commit from your own GitHub account so the history shows who built what.
- Only Saeed changes models and migrations. Ask Saeed for model changes to avoid
  migration conflicts.
- Add Django tests for the rules in your own feature.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the Git workflow.

## Team

| Member | Student ID | Phase 6 features |
|---|---|---|
| Saeed Alkaabi | 100063100 | Project setup and data model, C2 Departments and assets, C7 Dashboard, AI #5 Report summary |
| Ali Alawadhi | 100063186 | C1 Login and roles, C6 States and history, AI #2 Matching and ranking |
| Humaid Al Ali | 100062914 | AI gateway, AI #1 Classification, C5 Approve and transfer |
| Abdullah Alblooshi | 100061739 | C3 Publish and search, C4 Request and track, C8 Notifications, C9 Basic report |
