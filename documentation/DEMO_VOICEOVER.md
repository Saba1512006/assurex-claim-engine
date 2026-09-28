# Demonstration video — narration

Video: `AssureX_Demo.mp4` (1920 × 1080, 30 fps, 11 min 22 s, H.264 with AAC audio), recorded from the running
application against a freshly seeded database. Also delivered as two parts for upload limits: part 1 is 0:00–5:12 (up to Part 4), part 2 is
5:12–11:22.

* **Narration:** English, generated with the open-source Kokoro text-to-speech model (voice `af_heart`) from the script
  below, and placed at the timestamps shown. Declared in `AI_USAGE.md` §3.
* **On screen:** every narrated step also has a caption, and the element being discussed is outlined, so the video can
  be followed with the sound off.
* **Nothing is staged:** every claim, prediction and decision is produced live by the application; the recording is
  unedited.

## Chapters

| Time | Chapter |
|---|---|
| 0:04 | Title card: Warranty claims, checked twice |
| 0:29 | PART 1 · The live check |
| 1:32 | PART 2 · Customer journey |
| 3:36 | PART 3 · The decision |
| 5:13 | PART 4 · Demonstration cases |
| 6:57 | PART 5 · Manual review |
| 7:50 | PART 6 · Administration |
| 9:15 | PART 7 · Beyond the requirements |
| 10:57 | Closing card: Two models. One rulebook. |

## Script

| Time | On screen | Narration |
|---|---|---|
| 0:05 | **Title card: Warranty claims, checked twice** | Hi, and welcome to Assure X, a warranty claim engine built for TechWiz 7. Every claim is checked twice: once by a Python machine learning model, and once by a Google Teachable Machine image model. A configurable warranty policy engine then turns those results into a decision, and whenever the system is unsure, a person decides. |
| 0:30 | **PART 1 · The live check** | Let's start with the landing page, and its live check. |
| 0:37 | The live check runs a real sample claim through the whole pipeline | Right on the home page, this live check runs a real sample claim through the complete pipeline, the same code the product uses. |
| 0:45 | Clean fault: both models say Valid, no rule blocks it, so the claim is Likely Valid | Here's a clean fault. Both models predict Valid Claim, and no warranty rule blocks it, so the recommendation is Likely Valid. |
| 0:56 | Liquid damage: an excluded cause confirmed by a technician gives Likely Invalid | Now liquid damage. That cause is excluded by the policy, and a technician confirmed it, so a hard-fail rule makes it Likely Invalid. |
| 1:08 | Filed four days into the grace period: Uncertain Result, so a person reviews it | And this one was filed four days into the grace period. Confidence drops, the result is uncertain, so the claim goes to a person instead of being auto-decided. |
| 1:22 | Behind the card: two models feed the decision core, the policy engine and the outcome | Behind the card, you can see the flow: the Python model and the vision model feed a decision core, which applies the warranty policy and produces the outcome. |
| 1:33 | **PART 2 · Customer journey** | Part two: the customer journey. We'll register, add a product with O C R, and file a claim from start to finish. |
| 1:44 | User registration: every field is validated in the browser and on the server | First, a new customer creates an account. Every field is validated, both in the browser and again on the server. |
| 1:56 | Sign in with the new account | Now we sign in with the new account. |
| 2:01 | The customer dashboard: products, warranties, claims and pending actions | This is the customer dashboard. Products, warranties, claims, and anything waiting on the customer, all in one place. |
| 2:11 | Product registration: upload the purchase receipt and OCR reads it | To register a product, the customer simply uploads the purchase receipt, and O C R reads it. |
| 2:18 | OCR fills in product, model, serial number, purchase date, price, retailer and invoice number | In a moment, the product name, model, serial number, purchase date, price, retailer and invoice number are all filled in automatically. |
| 2:28 | The customer checks each extracted field before saving | The customer checks each extracted field before anything is saved. |
| 2:36 | The category sets the warranty length: standard or extended cover | The category sets the warranty length, with standard or extended cover. |
| 2:44 | The product and its warranty: coverage dates, status and documents | And here's the registered product, with its warranty coverage dates, status and documents. |
| 2:52 | Claim creation: choose the product | Now let's file a claim. Step one: choose the product. |
| 2:58 | Fault details: category, cause, start date and a description | Step two: the fault. Its category, the cause, when it started, and a short description. |
| 3:06 | Upload the receipt: it is read again and compared with the registered product | Step three: documents. The receipt is read again, and compared with the product on record. |
| 3:13 | OCR check: the serial number on the receipt matches the registered product | The serial number on the receipt matches the registered product, so this check passes. |
| 3:19 | Supporting evidence: warranty card, damage photo and serial-number photo | We add the supporting evidence: the warranty card, a photo of the damage, and a photo of the serial number. |
| 3:28 | Review the claim, then submit | Finally, a quick review, and we submit. |
| 3:37 | **PART 3 · The decision** | Part three: the decision. This is the heart of the system. |
| 3:44 | The verdict: the recommendation, both models and the consistency check | Within a couple of seconds, the claim is decided. At the top is the recommendation, and the time the whole pipeline took. |
| 3:53 | Python model: confidence for Valid, Invalid and Manual Review | On the left is the Python model. The claim's data is pre-processed into features, and the model gives a confidence for each of the three classes. |
| 4:04 | Teachable Machine: classifies the Claim Summary Card, with its own three confidences | On the right is Google Teachable Machine. It classifies an image, the Claim Summary Card, and gives its own three confidences. |
| 4:14 | Comparison: do the classes match, the confidence difference, and the consistency status | In the middle, the two models are compared: do the predicted classes match, how far apart are their confidences, and are they consistent? |
| 4:25 | Why this decision: the warranty rules and the decision-table row that matched | Below that, why this decision. Every warranty rule from the category policy is listed, with the decision table row that matched. |
| 4:35 | What moved the Python model: each input's effect on the prediction | For explainability, this shows which inputs moved the Python model, and by how much. |
| 4:42 | What the image model saw: claim facts only, never a prediction or a decision | And this is exactly what the image model saw. The card shows claim facts only, never a prediction or a decision. The shaded tiles show which parts drove its answer. |
| 4:57 | Claim status tracking: eight stages from filing to closing | The customer can track the claim through eight stages, from filing to closing. |
| 5:05 | Report generation: a PDF with the claim, evidence, both predictions, rules and decision | And with one click, a P D F report is generated, with the claim, the evidence, both predictions, the rules and the decision. |
| 5:14 | **PART 4 · Demonstration cases** | Part four: the demonstration cases. Valid, invalid, manual review, missing documents, contradictions, a boundary date, and a model disagreement. |
| 5:37 | Valid claim: both models agree Valid and no rule blocks it: Likely Valid | A valid claim. Both models agree it's valid, no rule blocks it, so it's Likely Valid. |
| 5:47 | Invalid claim: a hard-fail warranty rule decides it: Likely Invalid | An invalid claim. A hard-fail warranty rule decides it, so it's Likely Invalid. |
| 5:57 | Manual-review claim: a manual-review rule sends it to a person | A manual review claim. A review rule fires, so a person has to look at it. |
| 6:05 | Missing documents: the mandatory receipt is missing, so the claim waits | Missing document detection. The mandatory receipt isn't there, so the claim waits for more information, and the customer is told exactly what's needed. |
| 6:20 | Contradiction detection: conflicting evidence sends the claim to review | Contradiction detection. The dates and the evidence don't agree with each other, so the claim is routed to review. |
| 6:32 | Boundary case: filed four days into a seven-day grace period | A tricky boundary case. It was filed four days into a seven-day grace period. The confidence is low, so the result is uncertain. |
| 6:46 | Model disagreement: Python says Invalid, Teachable Machine says Valid, so a person decides | And a model disagreement. Python says invalid, Teachable Machine says valid. When the models disagree, the system never guesses. A person decides. |
| 6:58 | **PART 5 · Manual review** | Part five: manual review. |
| 7:11 | The reviewer queue: filters, risk levels and waiting time | Claims that need a person land in the reviewer's queue, with filters and risk levels. |
| 7:19 | The workbench: evidence, both models' scores and the warranty facts side by side | Let's open the disagreement case. The workbench puts the evidence, both models' scores and the warranty facts side by side. |
| 7:31 | Approve with a written comment, and a written reason for the override | The reviewer approves it, and writes a comment. Because this overrides the automated result, a written reason is required. |
| 7:42 | The decision is recorded, the customer is notified and the status changes | The decision is recorded, the customer is notified, and the claim's status changes. The override is kept in the audit trail. |
| 7:51 | **PART 6 · Administration** | Part six: administration. |
| 8:05 | Administrator dashboard: claims, automation rate, model agreement and workload | The administrator dashboard shows claim volume, the automation rate, model agreement and the review workload. |
| 8:15 | Charts: claims per week, recommendations, model agreement and confidence | The charts break down claims per week, recommendations, model agreement and confidence. |
| 8:24 | Analytics: frequent faults, rejection reasons, category trends and model evidence | Analytics shows the most frequent faults, the reasons claims are rejected, trends per category, and the evidence for both models. |
| 8:35 | Warranty policies are configuration: coverage, grace periods, exclusions and rule severity | Warranty policies are configuration, not code. Coverage, grace periods, excluded causes and rule severity can all be changed here, with version history. |
| 8:48 | Models: both installed with versions; the Teachable Machine export is uploaded and evaluated here | On the models page, both models are installed with their versions. A new Teachable Machine export can be uploaded and evaluated right here. |
| 9:00 | The audit trail: every login, upload, prediction, decision and override | The audit trail records every login, upload, prediction, decision and override. |
| 9:08 | Access control: roles, record scopes, invitations and blocked attempts | And access control manages roles, which records each role can see, invitations, and blocked attempts. |
| 9:16 | **PART 7 · Beyond the requirements** | Part seven: going beyond the requirements. |
| 9:24 | What-if simulator: try a stricter threshold on 225 stored test decisions | The what-if simulator lets an administrator try a stricter confidence threshold on all 225 stored test decisions, before changing anything. |
| 9:35 | Automation rate, review load and accuracy update instantly; nothing is saved until Apply | Watch the automation rate, the review load and the accuracy update instantly. Nothing is saved until you press apply. |
| 9:45 | Batch evaluation: run uploaded claim records through the real pipeline | Batch evaluation runs a file of claim records through the real pipeline, chunk by chunk. |
| 9:53 | 30 unseen test claims evaluated: accuracy against the labels, with a downloadable CSV | Thirty unseen test claims, evaluated, with accuracy against their labels, and a downloadable C S V. |
| 10:03 | Policy changes are previewed and versioned before they apply | Policy changes are previewed and versioned. And if a change affects a limit shown on the card, the system warns that the image model needs retraining. |
| 10:16 | Input safety: names take no digits and phone numbers take no letters | Input safety: names can't contain digits, and phone numbers can't contain letters. This is enforced in the browser and on the server. |
| 10:27 | Sign-in protection: five wrong passwords pause the account for one minute | Sign-in is protected too. After five wrong passwords, the account is paused for one minute, with a live countdown. |
| 10:38 | The public model card: metrics, confusion matrices and errors for both models | Finally, the public model card. Both models' metrics, confusion matrices and errors, read directly from the evaluation files. |
| 10:49 | The technical blog, also published on Medium | And there's a technical blog explaining how it was built, also published on Medium. |
| 10:58 | **Closing card: Two models. One rulebook.** | The Python model reaches eighty-nine point three percent, and Teachable Machine ninety-three point eight percent, on two hundred and twenty-five unseen test claims. Backed by two hundred and ninety-five automated tests. Two models, one rulebook, and a person whenever it matters. Thank you for watching. |
