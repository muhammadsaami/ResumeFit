# ResumeFit

ResumeFit is a production-minded resume improvement web app. It takes your resume (PDF, DOCX
or pasted text), parses it into structured data, scores its **ATS readiness** with a fully
deterministic, rule-based rubric, proposes **explainable, reversible** fixes, matches it against
a job description, and exports ATS-friendly **PDF / LaTeX / Overleaf** output.

Everything runs locally. There is **no external LLM and no paid service**: parsing, scoring,
auto-fixes, the fabrication guard and job matching are all rules and curated taxonomies you can
read in the source. Scores are an **estimate of ATS readiness**, not a guarantee of how any
commercial ATS will rank you, and the UI says so.

## What works

**Resume intake**
- Upload **PDF, DOCX, TXT** (max **5 MB**) or paste text.
- Real client and server validation with clear error messages; PDFs are parsed text-first
  (scanned-image PDFs without a text layer are rejected with a clear message, not OCR'd).
- Temporary data with a **one-hour expiry** and explicit delete; nothing is logged.

**Analysis (deterministic)**
- Canonical structured resume JSON: contact, summary, education, experience, projects,
  certifications and skills, with source-line traceability and a parsing-confidence signal.
- A **100-point ATS-readiness rubric** (contact, sections, standard headings, evidence, bullet
  quality, skills hygiene, dates, tone, cleanliness, length) where every point is tied to a
  check with an explanation and suggestion. Content-aware: a heading with no content does not
  earn its section points, and uncertain extraction downgrades rather than fabricates.
- A list of detected issues, each linked to the source line(s) that triggered it.

**Reviewable auto-fixes**
- Proposed changes for standard headings, dates, bullet formatting, first-person/filler wording,
  weak openers, past-role tense, duplicate skills, skill grouping and over-long bullets, plus
  advisory flags for missing contact/sections and possible personal details.
- A **fabrication guard** rates every rewrite `safe`, `needs_review` or `unsafe`; unsafe edits
  cannot be applied. No numbers, employers, titles, degrees, certifications or skills are ever
  invented.
- Accept, reject, or **edit** each proposal. The original resume is never overwritten; the
  effective resume is what gets re-scored, so the reported score always matches the accepted
  state. Accept/reject/edit are reversible.

**Job-description tailoring**
- Case-insensitive matching over a curated skill taxonomy plus keyword extraction.
- Matched skills, missing skills (reported, **never inserted** automatically), matched/missing
  keywords, and the skills demonstrated in your bullets (with evidence lines).
- A transparent **match percentage** with a plain-language explanation of exactly how it was
  computed (curated skills weighted 2× over free keywords).

**Export**
- Three original LaTeX templates - **Classic**, **Compact**, **Modern** - compiled to PDF with
  Tectonic, plus the `.tex` source and an Overleaf hand-off. PDFs use no ligature/hyphenation
  artifacts and carry working hyperlinks.

**UI**
- An inline **resume preview** that highlights matched job terms in place, flags lines with
  detected issues, shows evidence snippets, renders a **word-level diff** on each proposed
  change, and lets you jump from a finding to the relevant line. Premium cream/ink theme with
  the Fraunces + Inter type pairing.

## Tech stack

| Layer    | Technology                                                    |
| -------- | ------------------------------------------------------------- |
| Frontend | React, Vite, TypeScript, Tailwind CSS                         |
| Backend  | Python 3.11+, FastAPI, Pydantic v2, Uvicorn                   |
| Parsing  | pdfplumber (PDF), python-docx (DOCX), built-in decoding (TXT) |
| Export   | Tectonic (LaTeX), pypdf, reportlab (test fixtures)            |
| Tooling  | pytest, ruff, `tsc --noEmit` + `vite build`                   |

No database, accounts, Docker or external infrastructure are used.

## Prerequisites

- Python **3.11 or 3.12**
- Node.js **18+** and npm
- Windows PowerShell (commands below use PowerShell)
- For PDF export: a LaTeX engine. The compiler auto-detects Tectonic (a repo-local copy at
  `backend/.tools/tectonic/tectonic.exe`, or `tectonic` on your `PATH`), then `xelatex`, then
  `pdflatex`. Override with `RESUMEFIT_LATEX_COMPILER` (a name or full path, or `none` to
  disable). Without an engine the app still returns the `.tex` source and reports
  `compiler_unavailable` instead of failing.

## Backend setup (PowerShell)

```powershell
cd "backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install --upgrade pip
pip install -r requirements-dev.txt   # runtime + test/lint dependencies
uvicorn app.main:app --reload --port 8000
```

The API is at `http://localhost:8000` and interactive docs at `http://localhost:8000/docs`.

> If port 8000 is in use, pick another (e.g. `--port 8010`) and set `VITE_API_BASE_URL` in
> `frontend/.env` to match.

## Frontend setup (PowerShell, separate terminal)

```powershell
cd "frontend"
npm install
npm run dev            # open http://localhost:5173
```

The header shows a live backend connection indicator. Copy `.env.example` to `.env` only if you
need to override the API base URL.

## Tests and quality checks

**Backend** (from `backend`, venv active):

```powershell
.\.venv\Scripts\python.exe -m pytest -q          # full suite
.\.venv\Scripts\python.exe -m ruff check app tests
```

**Frontend** (from `frontend`):

```powershell
npm run typecheck   # tsc --noEmit
npm run build       # typecheck + production build
npm run preview     # serve the production build
```

Backend tests include regression suites for real-world PDF extraction edge cases
(hyphenated/camelCase line wraps, ligatures, wrapped bullets, education de-duplication) and
quality checks on generated LaTeX. Fixtures are privacy-safe placeholders.

## API reference

Base prefix: `/api/v1`

| Method | Path                                        | Description                                        |
| ------ | ------------------------------------------- | -------------------------------------------------- |
| GET    | `/health`                                   | Service health, version, uptime, stored count      |
| POST   | `/resumes`                                  | Create a resume from a file (multipart) or text    |
| GET    | `/resumes/{resume_id}`                      | Retrieve a previously processed resume             |
| DELETE | `/resumes/{resume_id}`                      | Delete temporary resume data                       |
| POST   | `/resumes/{resume_id}/analyze`              | Parse and score the stored resume                  |
| GET    | `/resumes/{resume_id}/changes`              | List proposed changes + effective analysis         |
| POST   | `/resumes/{resume_id}/changes/{id}/accept`  | Apply a proposed rewrite                           |
| POST   | `/resumes/{resume_id}/changes/{id}/reject`  | Reject a proposal and restore the original         |
| POST   | `/resumes/{resume_id}/changes/{id}/edit`    | Replace a proposal's text with your own            |
| POST   | `/resumes/{resume_id}/tailor`               | Match the resume against a job description         |
| GET    | `/resumes/{resume_id}/render/templates`     | List available templates                           |
| POST   | `/resumes/{resume_id}/render`               | Render the effective resume to PDF/LaTeX           |
| POST   | `/resumes/{resume_id}/overleaf`             | Prepare `.tex` for Overleaf                        |
| GET    | `/artifacts/{artifact_id}`                  | Download a generated PDF or `.tex`                 |

`POST /resumes` accepts either `multipart/form-data` (a `file` part and/or a `text` field) or
`application/json` with `{ "text": "..." }`.

Errors use a consistent envelope:

```json
{ "error": { "code": "file_too_large", "message": "File is too large. The maximum size is 5 MB." } }
```

Status codes: `201` created, `204` deleted, `400` malformed/empty input, `404` unknown resume or
change, `409` change conflict (the text changed under a pending edit), `413` file too large,
`415` unsupported content, `422` unprocessable (empty text, scanned PDF, advisory-only action).

### Auto-fix and tailoring behavior guarantees

- Advisory flags (`missing_contact`, `missing_section`, `personal_detail`, some
  `bullet_rewrite`) are never applied automatically.
- Accepting a rewrite re-parses and re-scores the effective text; the score always reflects
  accepted changes. A rewrite that would break parsing is never committed.
- Current-role bullets keep their tense (a live role legitimately mixes past achievements and
  present duties); tense normalization only applies to past roles.
- Missing skills from a job description are listed for review and are never inserted.

## Privacy and security notes

- Resume text is held in memory only and is **never logged**; logs contain request metadata
  (method, path, status) only.
- Filenames and MIME types are not trusted: extensions are checked and actual bytes are
  validated (magic numbers, structure, decodability).
- Resume IDs are opaque, unpredictable tokens (`secrets.token_urlsafe`).
- Data expires **one hour** after creation and is also removed by an explicit `DELETE`.

## Sample resume (development and tests only)

```
Aisha Khan
Email: aisha.example@example.com

Education:
Bachelor of Computer Applications, 2025

Project:
Student Management System

Skills:
Python, SQL, HTML, CSS

Experience:
Fresher
```

All test and sample names, emails and organisations are fictional placeholders. No employers,
work experience, certifications, metrics or skills beyond what a fixture contains are ever added.

## Project structure

```
backend/
  app/
    api/            # health, resume, analysis, change-review, tailor, render routes
    core/           # structured errors and handlers
    models/         # Pydantic request/response models
    services/       # extraction, parser, scoring, analyzer, autofix, guard,
                    # tailoring, review, latex, compiler, rendering, store, artifacts
    templates/latex # classic / compact / modern Jinja -> LaTeX
    config.py       # environment-driven settings
    main.py         # FastAPI app factory
  tests/            # pytest suite incl. corruption + quality regression
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  .env.example
frontend/
  src/
    api/            # typed backend client
    components/     # Header, Dashboard, AnalysisWorkspace, ResumePreview,
                    # ChangeReview, TailorPanel, ExportWorkspace
    lib/            # formatting + highlight + diff helpers
    types.ts
    App.tsx
  package.json
  .env.example
README.md
```

## Roadmap

Delivered: structured parsing, deterministic scoring, rule-based auto-fixes with source-line
traceability, fabrication guard, job-description tailoring, three LaTeX templates with safe PDF
generation, Overleaf export, and one-hour automatic deletion.

Possible next steps: DOCX export, additional templates, and broader extraction coverage for
unusual resume layouts. Scanned-PDF OCR remains explicitly out of scope.
