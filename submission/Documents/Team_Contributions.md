# Team contribution record (SRS final submission checklist)

The SRS asks for a record of each member's contribution and for commits from every team member. The
commit counts below come from `git shortlog -sne`; the contribution rows are the team's statement of who did
what, and each member should be able to explain the modules listed against their name.

## Group

| | |
|---|---|
| Group | **NN_DevStorm** |
| Project | AssureX Claim Engine — NextWave AI and ML (Aptech Limited) |
| Batch | 2609E2' |
| Faculty | Sir Minhaj |

| Student ID | Name | Role in the project |
|---|---|---|
| Student1525913 | Saba Noor | Team lead · integration, frontend direction, QA, documentation |
| Student1524867 | Muhammad Sami | Backend and ML pipeline developer · deployment |
| Student1509222 | Muhammad Ghanyan | Frontend design (Figma, colour palette, mobile checks) |
| Student1505677 | Muhammad Sami ur Rehman | Testing (sample claims, Chrome and mobile) |

## Commits on `main`

| GitHub account | Commits |
|---|---|
| Saba1512006 (Saba Noor) | 68 |
| sami2515 (Muhammad Sami) | 52 |

Counted on 28 September 2026 (120 commits, 23–28 September); per-day activity is in
`documentation/DEVELOPMENT_LOG.md`.

Regenerate before submitting: `git shortlog -sne main`. Every member should have commits under their own
account.

## Contributions

| Team member | Role | Main contributions (modules, documents, experiments) | Evidence (commits, files) |
|---|---|---|---|
| **Saba Noor** | Team lead · integration, frontend direction, QA, documentation | Led the v2 upgrade: integrated the leakage-free dataset, calibrated Python model, v3 Claim Summary Cards and RBAC into the application (AI-assisted, declared in `AI_USAGE.md`). Recorded and documented the Teachable Machine v3 results (93.8% test accuracy), the comparison report and the accuracy guards. Directed the frontend rebuild and the styling pass page by page (navbar, sign-in/register, dashboards, claim detail, workbench, footer, preloader, hero background), tested every change in the browser on Windows and reported the defects that were fixed (notifications link, menu scrolling, input validation on the Access page, lockout message, hero text clipping). Specified the form input rules and the one-minute lockout countdown. Published the technical blog on Medium; maintained the README, project report, test cases, installation guide, development log and AI declaration; merged the team's fork and pinned the model dependencies for release. | 68 commits (26–28 Sept) · `src/`, `templates/`, `static/`, `tests/`, `documentation/`, `reports/`, `AI_USAGE.md` |
| **Muhammad Sami** | Backend and ML pipeline developer · deployment | Built the first complete version of the application (23–26 Sept): multi-role registration and profiles; product registration and the common warranty interface; receipt/invoice upload with OCR extraction and verification; warranty tracking and expiry alerts; claim registration, fault evidence and repair history; document organisation, data validation and pre-processing; the algorithm comparison matrix; Claim Summary Card endpoint and Teachable Machine preview; confidence comparison and consistency thresholds; the warranty rule set, multi-category policies, four-source serial verification, contradiction, missing-document and duplicate detection; the decision engine, manual-review workflow and reviewer override audit trail; 8-stage tracking and notifications; admin analytics and search; reporting, audit and model-version telemetry; the first RBAC implementation. Deployed to PythonAnywhere and fixed its start-up errors; set up Render/gunicorn files; tuned the live check layout and the Linux/Windows TFLite requirements on 28 Sept. | 52 commits (23–26, 28 Sept) · `src/`, `templates/`, `policies/`, `sample_claims/`, `Procfile`, `render.yaml`, `requirements.txt` |
| **Muhammad Ghanyan** | Frontend design | Designed the login and dashboard pages in Figma and chose the colour palette used as the visual reference for the interface; checked the mobile view of the pages. | Figma designs shared with the team (no commits under a personal GitHub account) |
| **Muhammad Sami ur Rehman** | Testing | Ran the 11 SRS sample claims (`sample_claims/`) through the application and checked each result; tested the pages in Chrome and on mobile; reported the defects found to the team for fixing. | Test runs reported to the team (no commits under a personal GitHub account) |

## Work sessions / meetings (optional)

| Date | Members present | Work done |
|---|---|---|
| | | |

See also `AI_USAGE.md` (AI tools used and who verified their output) and
`documentation/DEVELOPMENT_LOG.md` (dated log of work, problems and fixes).
