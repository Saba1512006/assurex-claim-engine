# Demonstration video — voice-over script

Video: `AssureX_Demo.mp4` (1280 × 720, 7 min 33 s, no audio). Record your voice over it in any editor
(for example Clipchamp on Windows: import the video, *Record → Audio*, speak along with the captions, export as .mp4).
Each line starts at the time shown; the on-screen caption says the same thing, so reading the line as the caption
appears keeps the voice in step. Chapter cards stay on screen for about three seconds.

| Time | On screen | Say |
|---|---|---|
| 0:03 | **ASSUREX CLAIM ENGINE Warranty claims, checked twice** (title card) | Welcome to AssureX Claim Engine. Every warranty claim is checked twice, by a Python model and a Teachable Machine image model, and a person decides whenever they are unsure. |
| 0:10 | **PART 1 The live check** (title card) | Part 1: The live check. The landing page runs real sample claims through the complete pipeline. |
| 0:14 | caption | AssureX Claim Engine: every warranty claim is checked by two independent models and a warranty policy engine. |
| 0:19 | caption | The live check runs a real sample claim through the whole pipeline. |
| 0:22 | caption | Clean fault: both models predict Valid Claim; no blocking rule fires; Likely Valid (rule D07). |
| 0:31 | caption | Liquid damage: excluded cause confirmed by a technician; a hard-fail rule gives Likely Invalid (rule D01). |
| 0:39 | caption | Filed 4 days into the grace period: low confidence, Uncertain Result, so the claim goes to a person. |
| 0:46 | caption | Behind the card: the Python model and the vision model feed the decision core, the policy engine and the outcome. |
| 0:51 | **PART 2 Customer journey** (title card) | Part 2: Customer journey. Registration, product and warranty registration with OCR, claim creation, evidence upload and submission. |
| 0:56 | caption | User registration: a customer creates an account (every field is validated in the browser and on the server). |
| 1:09 | caption | Login with the new account. |
| 1:14 | caption | The customer dashboard: products, warranties, claims and pending actions. |
| 1:19 | caption | Product registration: upload the purchase receipt; OCR reads it. |
| 1:23 | caption | OCR extraction: product, model, serial number, purchase date, price, retailer and invoice number are filled in. |
| 1:28 | caption | Extracted-data verification: the customer checks each field before saving. |
| 1:35 | caption | Warranty registration: the category sets the warranty length; standard or extended cover. |
| 1:40 | caption | The product and its warranty: coverage dates, status and documents. |
| 1:47 | caption | Claim creation: choose the product. |
| 1:52 | caption | Fault details: category, cause, the date it started, and a description. |
| 2:00 | caption | Receipt and document upload: the receipt is read again and compared with the registered product. |
| 2:05 | caption | OCR check: the serial number on the receipt matches the registered product. |
| 2:11 | caption | Supporting evidence: warranty card, damage photo and serial-number photo. |
| 2:15 | caption | Review the claim, then submit. |
| 2:26 | **PART 3 The decision** (title card) | Part 3: The decision. Python prediction, Claim Summary Card, Teachable Machine prediction, model comparison, warranty rules and the final decision. |
| 2:30 | caption | Data pre-processing turns the claim into model features; the Python model scores all three classes. |
| 2:34 | caption | Python model confidence for Valid, Invalid and Manual Review. |
| 2:37 | caption | The Claim Summary Card is generated and Google Teachable Machine classifies it, with its own three confidences. |
| 2:41 | caption | Comparison: predicted-class match, the top-class confidence difference (Δ) and the consistency status. |
| 2:47 | caption | Warranty-rule execution: 16 checks from the category policy, with the decision table's reason. |
| 2:53 | caption | The image model saw only claim facts: the card never shows a prediction or a decision. |
| 2:59 | caption | Missing documents, contradictions and duplicate indicators are listed with the evidence. |
| 3:09 | caption | Claim status tracking: eight stages from filing to closing. |
| 3:15 | caption | Report generation: a PDF with the claim, the evidence, both predictions, the rules and the decision. |
| 3:18 | **PART 4 Demonstration cases** (title card) | Part 4: Demonstration cases. Valid, invalid and manual-review claims, missing documents, contradictions, a boundary date and a model disagreement. |
| 3:31 | caption | One valid claim: both models agree Valid and no rule blocks it: Likely Valid. |
| 3:36 | caption | One invalid claim: a hard-fail warranty rule decides it: Likely Invalid. |
| 3:41 | caption | One manual-review claim: a manual-review rule sends it to a person. |
| 3:47 | caption | Missing-document detection: the mandatory receipt is missing, so the claim waits (rule D03). |
| 3:56 | caption | Contradiction and duplicate detection: conflicting evidence sends the claim to review (rule D02). |
| 4:05 | caption | Tricky boundary case: filed 4 days into the 7-day grace period; low confidence, Uncertain Result. |
| 4:10 | caption | Model disagreement: Python says Invalid, Teachable Machine says Valid, so a person decides. |
| 4:14 | **PART 5 Manual review** (title card) | Part 5: Manual review. The reviewer queue, the three-column workbench and a decision with a written override. |
| 4:26 | caption | Manual-review routing: the reviewer's queue, with filters and risk levels. |
| 4:32 | caption | The reviewer workbench: evidence, both models' scores and the warranty facts side by side. |
| 4:38 | caption | Reviewer comments or override: approve with a written reason; it is kept in the audit trail. |
| 4:47 | caption | The decision is recorded, the customer is notified and the claim status changes. |
| 4:50 | **PART 6 Administration** (title card) | Part 6: Administration. Dashboard, analytics, configurable warranty policies, model management and the audit trail. |
| 5:04 | caption | Administrator dashboard: claims, automation rate, model agreement and review workload. |
| 5:10 | caption | Charts: claims per week, recommendations, model agreement and confidence. |
| 5:19 | caption | Analytics: frequent faults, rejection reasons, category trends and model evidence. |
| 5:28 | caption | Warranty policies are configuration: coverage, grace periods, exclusions and rule severity, with version history. |
| 5:37 | caption | Models: both installed with versions; the Teachable Machine export is installed and evaluated here. |
| 5:42 | caption | The audit trail records every login, upload, prediction, decision and override. |
| 5:48 | caption | Access control: roles, record scopes, invitations and blocked attempts. |
| 5:51 | **PART 7 Beyond the requirements** (title card) | Part 7: Beyond the requirements. What-if simulation, batch evaluation, explainability, policy versioning, input safety and a public model card. |
| 5:57 | caption | What-if simulator: try a stricter confidence threshold on all 225 stored test decisions before changing it. |
| 6:03 | caption | The automation rate, review load and accuracy update instantly; nothing is saved until Apply. |
| 6:09 | caption | Batch evaluation: upload claim records and run them through the real pipeline, chunk by chunk. |
| 6:25 | caption | 30 unseen test claims evaluated: accuracy against the labels, with a downloadable CSV. |
| 6:35 | caption | Explainability: which inputs moved the Python model, and which card tiles drove the image model. |
| 6:41 | caption | Policy changes are previewed and versioned; a change to a limit shown on the card warns that the image model needs retraining. |
| 6:47 | caption | Input safety: names take no digits, phone numbers take no letters; checked in the browser and on the server. |
| 6:58 | caption | Sign-in protection: five wrong passwords pause the account for one minute, with a live countdown. |
| 7:11 | caption | The public model card: both models' metrics, confusion matrices and errors, read from the evaluation files. |
| 7:19 | caption | The technical blog, also published on Medium. |
| 7:24 | **ASSUREX CLAIM ENGINE Two models. One rulebook.** (title card) | That is AssureX: two models, one rulebook, and a person whenever they are unsure. The Python model scores 89.3 percent and Teachable Machine 93.8 percent on 225 claims neither model saw in training, and the project is covered by 295 automated tests and 34 browser tests. Thank you for watching. |

Recorded from the running application with both models installed (Python `v2.0.0`, Teachable Machine
`gtm-514702678b8c`) on a freshly seeded database; every screen is the real application, nothing is mocked.
