# Building AssureX: two models, one rulebook, and why our first 100% was a bug

*How we built a warranty-claim engine that combines a Python classifier, a Google Teachable Machine image
model and a configurable rule engine — and what we learned when our first version scored suspiciously well.*

## The business problem

A warranty claim looks simple: a customer says a product broke, the manufacturer pays for the repair.
Behind that sentence is a checklist that service centers run by hand thousands of times a month. Was the
product bought when the customer says? Is the warranty still active, or inside its grace period? Is the
fault covered, or is it water damage the policy excludes? Does the serial number on the unit match the
receipt? Has someone already claimed on this invoice? Was the product opened by an unauthorised repair
shop?

Every one of those checks is easy on its own. Together they are slow, and different people apply them
differently. The same claim can be approved on Monday and rejected on Tuesday. Fraud slips through when a
receipt is reused for a second unit. Honest customers wait days for a decision that could have taken
seconds. AssureX automates the first pass, explains every recommendation, and sends a claim to a human
whenever the evidence is not clear.

## Background and why it matters

Warranty cost goes straight to a manufacturer's bottom line, and a badly handled claim costs a customer.
Two properties matter more than raw accuracy: **consistency** (the same facts always get the same
answer) and **accountability** (anyone can see why an answer was given, and who changed it). That pushed us
towards a design where machine learning supports decisions but a readable policy stays in charge, and
where nothing happens without leaving a record.

## The proposed solution

A customer — or a service-center employee helping a walk-in customer — registers a product with its
receipt, then files a claim in four steps: pick the product, describe what happened, attach evidence,
review. While they type, a checklist tells them what is missing, whether the reporting deadline is close,
and whether the cause they chose is excluded for that product category.

On submission the claim is evaluated twice, independently:

* a **Python classification model** reads the structured claim record;
* a **Google Teachable Machine** image model reads a picture of the same claim — the *Claim Summary Card*.

A **rule engine** checks the category's warranty policy, and detectors look for **contradictions** and
**duplicates**. A **decision table** combines everything into one of three recommendations: *Likely Valid*,
*Likely Invalid* or *Manual Review Required*. Reviewers work a queue of the uncertain claims; customers
follow their claim through eight stages; administrators get dashboards, analytics, exports and an audit
trail.

## Application architecture

The application is Flask with SQLAlchemy. Requests pass through an access-control layer before they reach
a blueprint (auth, products, claims, reviewer, admin). Blueprints call services — claim lifecycle,
documents, notifications, alerts, analytics, exports, PDF reports — and the evaluation pipeline:

1. document service (validate by magic bytes, store under a random name, SHA-256, OCR);
2. contradiction and duplicate detectors;
3. feature builder, producing exactly the columns the model was trained on;
4. rule engine driven by `policies/<category>.json`;
5. Python model → probabilities for all three classes;
6. card renderer → Teachable Machine → probabilities for all three classes;
7. consistency status and decision table driven by `config/decision_policy.json`.

Every run writes a new, immutable evaluation row holding the inputs, both model versions (hashes of the
model files), the card's hash, the thresholds and the decision trace. Updating a model never rewrites a
past result.

## Dataset creation

The competition gives no dataset, so we generated one: 1,500 claims, 500 per class, across consumer
electronics, home appliances and industrial tools, split 70/15/15 with stratification (1,050 / 225 / 225).

Our first generator worked backwards: *pick a class, then invent a claim that looks like it*. That is the
natural way to think about test data and it is exactly wrong for machine learning. The second generator
works forwards, the way real claims arrive. It samples each claim's attributes from overlapping,
realistic distributions — where in the warranty life the claim falls, how long the customer waited, what
caused the damage, how sure the technician is, repair history, which documents were attached — with no
knowledge of the class. Then it **derives** the label by applying the warranty policy, and flips 4% of
labels to simulate two reviewers disagreeing. Claim IDs are assigned after shuffling.

The scenarios that emerge cover what the brief asks for: normal covered defects, expired warranties,
claims inside the grace period, excluded damage, missing documents, contradictory dates, serial
mismatches, unauthorised repairs, repeat repairs, possible duplicates and late reporting.

## Dataset challenges

Three problems taught us the most.

**Label leakage.** Version 1 had a column called `damage_type` whose values mapped one-to-one onto the
class — "Hardware Defect" was always valid. Any model learned that single column and scored 100%. Worse,
the claim IDs were ordered by class (1–500 valid), so even the ID leaked. We now run a *leakage audit*
before training: a small decision tree is trained on each feature alone, and training stops if any single
feature predicts the class above 90%. The best single feature today, days to expiry, reaches 53%.

**Train/serve skew.** The web form offered damage types that the training data had never seen, and an
encoder configured to "ignore unknown values" silently turned them into zeros. The model then scored claims
it had never seen anything like. Now one vocabulary module feeds the generator, the form, the policies and
the encoder; unknown values raise an error; and a test renders the claim form and checks that its options
equal the training values.

**Rare scenarios.** Late reporting is only 23 of 1,500 claims. The model sees few examples and misses some
of them — which is fine, because the rule engine never misses them.

## Python model development

Pre-processing turns a claim into 20 features: eight numeric (price, warranty length, product age, days to
expiry, reporting delay, diagnostic confidence, repair count, missing-document count), ten binary
(documents present, extended warranty, serial match, unauthorised repair, duplicate invoice, date
conflict) and two categorical (category, damage cause). Numbers are standardised for the linear model;
categories are one-hot encoded with a fixed vocabulary. The encoder and model are saved as **one** pipeline
file, so they can never drift apart.

## Algorithms compared

We compared three algorithms with stratified 5-fold cross-validation on the training set, then on the
validation set:

| Algorithm | CV macro-F1 | Validation macro-F1 |
|---|---|---|
| Logistic regression | 0.739 | 0.726 |
| Random forest | 0.922 | 0.942 |
| HistGradientBoosting | 0.913 | **0.947** |

The model is chosen on **validation**; the test set is touched exactly once at the end. (Version 1 picked
the model by its test score, which quietly turns the test set into training data.) The winner is wrapped
in sigmoid calibration so that "80% confident" means right about 80% of the time — essential, because the
comparison between our two models is built on those confidence values.

On 225 unseen test claims the calibrated model reaches **89.3% accuracy**, macro-F1 89.2%, ROC-AUC 0.948 and
an expected calibration error of 0.082. The SRS asks for 85%. Given the 4% label noise, the practical
ceiling is about 96%.

## Google Teachable Machine training and the Claim Summary Card

The second model is an image classifier trained in the browser with Google Teachable Machine on pictures of
claims. The card had to be redesigned before that could work.

Version 1 cards were 640 × 420 landscape images full of 12-pixel text. Teachable Machine centre-crops every
upload to a square, which cut off both side columns; and an image model cannot read small text anyway. The
fonts also fell back to a bitmap font on the Linux server, so live cards looked different from training
cards.

Version 2 cards are 600 × 600 and use fonts bundled with the application. They drew every fact as a small
grey shape in a fixed position: bars for warranty life, reporting delay and diagnostic confidence, hatched
tiles for missing documents, pips for category and damage cause. It looked tidy and it failed: the real
Teachable Machine model trained on those cards scored 54.2% on the test cards. Teachable Machine does not
retrain the image network; it puts a small classifier on top of frozen ImageNet features, and at 224 × 224
pixels thin grey bars look nearly the same whatever their length. We rebuilt Teachable Machine's trainer
offline (`notebooks/tm_replica_check.py`) and it reproduced the failure (58–66%), which told us the card,
not the training run, was the problem.

Version 3 shows each fact against its policy limit as one of nine large tiles in a fixed 3 × 3 grid —
coverage, reporting time, damage cause, receipt, supporting evidence, serial number, dates, invoice and
repairs. A tile's colour and glyph change with the fact (within coverage, grace period or coverage ended;
reported in time or late; covered or excluded cause), and a colour band shows the category. The same
replica now scores 92.9–94.2% on the test cards, and the real Teachable Machine model trained on the
version 3 cards scored 93.8% (validation 97.3%, macro F1 93.8%), agreeing with the Python model on 92.9% of
the test claims. Text is still there, for humans. The card never shows a
prediction, a confidence, a rule outcome or a decision.

Each training claim is drawn twice with small, label-preserving variations — background tint, date format,
a slight rotation, blur and JPEG quality — giving 2,100 training images. Validation and test cards are
rendered once each and never uploaded to Teachable Machine. The exported TensorFlow Lite model runs inside
the application; if it is missing, the system says so and sends the claim to a reviewer rather than
deciding on one model.

## Python integration

The web application never retrains a model and never silently falls back to a different one. The Python
model is loaded once per process from the pipeline file; its version string embeds the file's hash. The
feature builder that feeds it lives in the application, and the training script imports the *same* feature
lists. If the file is missing or was pickled by an incompatible library version, the claim is still
evaluated by the rules, the model is marked unavailable, and the claim is routed to manual review with a
clear message.

## Model prediction comparison

For each claim the application shows both predicted classes side by side with all three probabilities,
whether the classes match, and the Claim Summary Card that the image model saw. The comparison ends in one
of five statuses. If either model's top confidence is below 0.60 the result is an **Uncertain Result**. If
the classes differ it is a **Model Disagreement**. Otherwise the gap between the two top confidences decides:
up to 0.10 is a **Strong Match**, up to 0.25 an **Acceptable Match**, anything larger a **Weak Match**.

## Confidence-score comparison

The confidence difference is |Python top confidence − Teachable Machine top confidence|. The two models are
trained on different representations and will never agree exactly, so the thresholds absorb normal
variation. Disagreement, uncertainty and weak matches all send the claim to manual review. All three
thresholds live in a configuration file that administrators edit in the app, and each evaluation stores the
thresholds it used.

## Warranty-rule design

Each product category has a JSON policy: coverage length, standard and extended terms, grace period,
reporting deadline, covered faults, excluded damage causes, how sure a technician must be to confirm an
exclusion, repeat-repair threshold, repair and replacement conditions, mandatory and supporting documents,
and three lists of rules — hard-fail, manual-review and warning. The engine knows sixteen checks. Which
list a check is in decides its severity; a check in no list is switched off.

The final decision is a table read top to bottom, first match wins: a hard-fail rule makes a claim *Likely
Invalid*; contradictions, duplicates, a missing mandatory document, model disagreement or uncertainty, or a
manual-review rule make it *Manual Review Required*; only then do the two models decide — both Invalid gives
*Likely Invalid*, both Valid gives *Likely Valid*; anything else goes to a reviewer. Changing the decision
logic, adding an exclusion or moving a threshold is a configuration edit, not a code change — which is what
the competition's "surprise modification" round asks for, and each of those modifications has a test.

## OCR and document processing

Receipts are read with pdfplumber (text PDFs) and Tesseract (photos and scans). We extract invoice number,
purchase date, product name, model, serial number, retailer, amount and warranty length with labelled
patterns only. The first version also compared text against hard-coded lists of known retailers and
products — it worked beautifully on our demo receipts and would have failed on any hidden test receipt, so
it is gone. Identifiers must contain a digit, so the word "Invoice" is never mistaken for an invoice
number. Every extracted value is shown to the user, who confirms or corrects it; corrections are audited.
Files are validated by their first bytes, not their extension: a text file renamed to `.png` is refused.

## Difficulties encountered

* Writing a generator that does **not** know the answer was harder than writing one that does.
* Making image-model inputs model-friendly meant designing a picture for a neural network, not a person.
* Keeping one vocabulary across form, dataset, model, policies and cards required a test that renders the
  form.
* Access control for four roles needed record scope, not just role checks: a service-center employee must
  see their own center's claims and nothing else, and a reviewer must not approve a claim they filed.

## Model errors

On the test split the Python model's weakest spot is Invalid claims predicted as Manual Review (8 of 75).
Of the 14 Invalid claims it misses, 5 are late-reporting cases (rare in training), 4 carry deliberately
flipped labels, 3 are excluded-damage claims with a diagnosis right at the threshold, and 2 sit on the
expiry boundary. Every one of those is a hard-fail rule in the policy, so the rule engine still rejects them
correctly. That is the point of combining a model with rules: the model generalises, the rules guarantee.

## Model disagreement cases

Disagreement is information, not failure. When the two models disagree the claim goes to a reviewer, who
sees both predictions, every rule result and the evidence on one page. As a design check we simulated an
image model that always agrees with the Python model: the rules and decision table then map 93% of test
claims to their labelled class, and two-thirds of the remaining differences are the noisy labels. The
measured comparison with the real Teachable Machine model is produced by one script
(`reports/generate_comparison_report.py`) as soon as the export is installed.

## Testing results

197 automated tests run in about 25 seconds: rule boundaries (last day of cover, first day after the grace
period, the reporting deadline ±1 day, the exclusion threshold), contradiction and duplicate detection,
OCR patterns, upload validation, both model runtimes, all five consistency statuses, the eleven
demonstration cases from the competition brief, full HTTP journeys from registration to approval, and the
security controls below. We also render every page for every role and take browser screenshots on desktop
and phone widths.

## Security considerations

Access is denied by default. Each role holds a list of permissions, each permission a scope — own records,
own service center, the review queue, or everything — and each action passes business constraints:
reviewers cannot decide claims they filed, claims move only along allowed transitions, overriding the
automated recommendation needs a written reason, and administrators cannot demote themselves or the last
administrator. A record outside your scope returns "not found", so identifiers cannot be probed. Users are
reloaded from the database on every request; a role change or disabled account signs them out everywhere.
Sign-in errors never reveal whether an email exists, five failures lock the account, forms carry CSRF
tokens, and the Content-Security-Policy forbids inline and third-party scripts. Every sensitive action —
including blocked access attempts — goes to an append-only audit log.

## Limitations

The dataset is synthetic; real claims will need retraining and recalibration. The Teachable Machine model
must be trained in the browser and re-exported whenever the card design changes. Image OCR depends on
Tesseract being installed on the server. Duplicate text detection is lexical, not semantic. SQLite suits a
single server; larger deployments should move to PostgreSQL.

## Lessons learned

* **Distrust a perfect score.** 100% accuracy on generated data is almost always leakage.
* **Select on validation, report on test, once.**
* **Calibrate before you compare confidences** between two models.
* **One vocabulary everywhere**, enforced by tests, prevents the quietest bugs.
* **Rules and models are partners.** Models generalise; rules guarantee the policy; the decision table makes
  their relationship explicit and editable.
* **Record everything**, including the model versions that produced each answer.

## Future enhancements

Retraining on real claims with drift monitoring; learning from reviewer overrides; image-based damage
detection on customer photos; semantic duplicate detection; email and SMS notifications; an API for
service-center systems; and multi-manufacturer tenancy.
