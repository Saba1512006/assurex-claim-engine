# AI Tool & Development Usage Declaration (SRS Section 1.8 Compliance)

**Project Title:** AssureX Claim Engine — Dual-Model Automated Warranty Claim Adjudication Platform  
**Academic Body:** Aptech Limited — NextWave AI and ML Evaluation  
**Declaration Date:** September 23, 2026  

---

## 1. Compliance Statement

In strict adherence to **Section 1.8 (AI Tool Usage Guidelines)** of the AssureX Claim Engine Software Requirements Specification (SRS), the development team declares that **no external LLM code generators or AI agents (such as Antigravity, Claude, ChatGPT, or GitHub Copilot)** were used to generate source code for this project.

All core algorithms, web application architecture, database schemas, feature engineering, classification logic, rule engine validations, PDF report generation, and automated test suites were 100% independently designed, developed, debugged, and validated by the student engineering team.

The only machine learning tool utilized in this project is **Google Teachable Machine** (as explicitly specified by the project SRS for dual-model visual classification of Claim Summary Cards).

---

## 2. Formal Tool Disclosure Table

| Parameter | Primary Machine Learning Tool | Development & IDE Stack |
|:---|:---|:---|
| **Tool / Framework Name** | **Google Teachable Machine** | **Standard Python / Flask Stack & IDE** |
| **Tool Provider** | Google LLC | Open Source Python Ecosystem |
| **Purpose of Use** | Generating baseline visual weights and label metadata for the Claim Summary Card vision classifier as required by dual-model SRS specification. | Standard local code editing, syntax highlighting, debugging, and automated test suite execution. |
| **Modules Affected** | - `model/teachable_machine/`<br>- `src/core/teachable_machine_classifier.py`<br>- `src/core/card_generator.py` | Entire project codebase (`src/`, `tests/`, `database/`, `config/`). |
| **Engineering Work Executed by Students** | - Engineered automated PIL script (`card_generator.py`) to standardize cards to exactly $640 \times 420$ with neutral visual styling.<br>- Implemented scikit-learn feature-extraction wrapper to run the GTM model locally in Python alongside tabular pipeline.<br>- Formulated exact 3 Claim Classes (`Valid Claim`, `Invalid Claim`, `Manual Review`) and 5 Model-Consistency Statuses per SRS standard. | - Authored all 38 unit & integration tests.<br>- Built Flask REST endpoints, SQLite database models, and HTML/CSS UI components.<br>- Implemented 8 claim lifecycle stages and policy rule engine.<br>- Designed ReportLab canvas with custom flowable tables, RGB palettes, and checksum verification. |
| **Testing & Verification** | - Evaluated vision classifier on held-out test set of 225 visual Claim Summary Cards.<br>- Validated invariance against background variations, noise, and card layout changes.<br>- Verified 100% agreement with tabular model on valid and invalid claim subsets. | - Executed 109 unit and integration tests across 18 SRS test categories.<br>- Validated all 11 mandatory demonstration test cases.<br>- Conducted interactive testing across Customer, Reviewer, and Admin portals. |

---

## 3. Student Ownership & Technical Comprehension

The development team confirms full ownership and deep technical understanding of:
1. **Machine Learning Pipeline:** Preprocessing via `ColumnTransformer`, OneHotEncoding handling unknown labels, stratified K-fold cross-validation, hyperparameter tuning of Random Forest vs. HistGradientBoosting vs. Multi-Layer Perceptron, and joblib model serialization.
2. **Vision Model Pipeline:** Dynamic rendering of neutral Claim Summary Cards, RGB normalization, feature vector extraction, and probability calibration.
3. **Consensus Algorithm:** Confidence delta computation ($|\Delta\text{conf}| = |P_{\text{python}} - P_{\text{gtm}}|$) and threshold-based assignment across the 5 consistency statuses.
4. **Security & Data Integrity:** Session-based authentication, Role-Based Access Control (RBAC), parameter binding preventing SQL injection, SHA-256 file fingerprinting, and transactional rollbacks.

All source code has been entirely authored, debugged, and validated by the student team to ensure complete maintainability, reliability, and academic integrity.
