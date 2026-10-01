# Micro-Empathy AI

A hackathon prototype for AI-assisted prioritization of government service complaints. Citizens can submit a written or browser-transcribed report; officers receive a queue ordered by estimated urgency, with critical reports highlighted for human verification.

> **Safety note:** This prototype does not perfectly detect emergencies or human emotions and cannot guarantee emergency detection. Priority labels are decision support only. Officers must verify critical complaints and follow local emergency response procedures.

## Problem
Government complaint queues can mix routine service requests with reports that may need urgent attention. Important context can be difficult to spot quickly, especially when a resident describes a situation in their own words or uses a regional language.

## Solution
Micro-Empathy AI captures citizen reports by text or browser speech recognition, analyzes complaint content with a modular rule-based service, and places higher estimated priorities first in an officer dashboard. It provides transparent factors and explanations rather than making a final response decision.

## Features
- Citizen intake with English and Tamil language selection.
- Browser Web Speech API transcription where supported by the browser.
- Modular, content-based priority analysis for medical, danger, accident, fire, vulnerable-person, service interruption, and urgency signals.
- SQLite persistence and a JSON API for submissions, queue retrieval, status updates, and demo data.
- Priority-sorted officer dashboard with statistics, human-verification alert, status workflow, and optional browser notifications.
- Demo complaint generator with normal, high, and critical examples.
- Mobile-responsive interface, accessible form labels, loading/empty states, and escaped complaint display.

## Architecture

1. `templates/` renders the citizen intake and officer dashboard pages.
2. `static/js/app.js` handles form submission, Web Speech API, dashboard refresh, and status actions.
3. `app.py` validates API requests, calls the analysis service, and stores records in SQLite.
4. `services/priority_engine.py` returns a priority, score, detected factors, explanation, and recommended action. This is the replaceable integration point for a future NLP/LLM service.
5. `services/speech_service.py` maps the selected language to browser speech-recognition locales. Audio processing happens in the browser; no audio is uploaded to Flask.

## Tech stack
- Frontend: HTML5, CSS3, vanilla JavaScript
- Backend: Python 3 and Flask
- Database: SQLite
- Speech: browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
- AI/NLP prototype: explainable Python content rules; no external API or secret key

## Folder structure

```text
micro-empathy-ai/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── database/
│   └── .gitkeep
├── services/
│   ├── __init__.py
│   ├── priority_engine.py
│   └── speech_service.py
├── templates/
│   ├── index.html
│   └── dashboard.html
└── static/
    ├── css/style.css
    └── js/app.js
```

The SQLite database is created automatically at `database/complaints.db` when the app starts. Database files are excluded from Git.

## Installation

Open this project folder in VS Code and run these commands from the project root:

```powershell
python -m venv venv
```

Windows (Command Prompt):

```bat
venv\Scripts\activate
```

Windows (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python app.py
```

Then open: <http://127.0.0.1:5000>

## Demo instructions
1. Open the citizen page and submit a complaint or use an example.
2. Open **Officer dashboard**.
3. Choose **Load demo data**. The critical medical-equipment/power complaint should appear above the accident and routine outage examples.
4. Review detected factors and use the status actions to acknowledge, start, or resolve cases.
5. Select **Enable alerts** to request browser notification permission for newly arriving critical reports. The dashboard alert is shown regardless of notification permission.

Demo complaints:

- Normal: `Enga area-la EB current poiduchu.`
- High: `Road-la accident nadandhirukku. Immediate help venum.`
- Critical: `Enga veetla medical equipment depend pannura patient irukanga. Current immediately venum.`

## API endpoints
- `GET /` - citizen intake page
- `GET /dashboard` - officer dashboard
- `POST /api/complaints` - create a complaint (`complaint_text`, `language`)
- `GET /api/complaints` - get priority-sorted complaints and counts
- `PATCH /api/complaints/<id>/status` - update a complaint (`status`)
- `POST /api/demo-data` - insert the three demo complaints

Allowed languages: `en`, `ta`. Allowed statuses: `NEW`, `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`.

## Example API request

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/complaints -ContentType 'application/json' -Body '{"complaint_text":"Road-la accident nadandhirukku. Immediate help venum.","language":"ta"}'
```

## Limitations
- Rules are keyword/context heuristics, not a trained model. They can miss emergencies, misunderstand wording, or assign an incorrect priority.
- Browser speech recognition availability, language support, and data handling vary by browser. The prototype does not upload audio to its server.
- The interface is a local demonstration, not an authenticated or production government case-management system.
- The prototype does not integrate dispatch, location verification, or live government service data.

## Safety considerations
- Do not rely on a priority score to dispatch help, deny a service, or decide that a complaint is safe.
- Officers must verify critical reports and independently assess all reports using applicable protocols.
- Voice stress or vocal characteristics are not used for classification.
- Do not submit real sensitive personal information in a public demo. Add authentication, access controls, retention policies, audit logging, and security review before handling real complaints.
- Any future API credentials should be supplied via environment variables and never committed to source control.

## Future improvements
- Replace or augment the rule engine behind the same service interface with an evaluated NLP/LLM provider.
- Add multilingual evaluation datasets, confidence calibration, fairness checks, and officer feedback loops.
- Introduce authenticated roles, assignment, audit logs, and production-grade privacy/retention controls.
- Add optional location capture and integrations with verified service-status systems.
- Evaluate speech-to-text quality across supported browsers and languages.
