# Demonstration video — narration

Video: `demo_video/AssureX_Demo.mp4` — one file, 13 min 37 s, 1920 × 1080, 30 fps, H.264 with AAC audio,
recorded from the running application against a freshly seeded database. Download:
https://github.com/Saba1512006/assurex-claim-engine/blob/demo-video/AssureX_Demo.mp4

* **Narration:** English, generated with the open-source Kokoro text-to-speech model (voice `af_heart`) from the script
  below, and placed at the timestamps shown. Declared in `AI_USAGE.md` §3.
* **On screen:** every narrated step also has a caption, and the element being discussed is outlined, so the video can
  be followed with the sound off.
* **All four roles** are shown signed in: customer (Parts 2–3), claim reviewer (Part 5), service-center staff
  (Part 6) and administrator (Parts 4, 7 and 8).
* **All 11 SRS demonstration cases** are shown in Part 4, each decided live: valid, invalid, manual review,
  expired warranty, missing document, duplicate, contradiction, serial mismatch, unauthorised repair,
  boundary date and model disagreement.
* **Nothing is staged:** every claim, prediction and decision is produced live by the application; the recording is
  unedited.

## SRS §1.10 item 13 — where each required step is shown

| Required in the video | Time |
|---|---|
| User registration or login | 1:44 |
| Product registration | 2:12 |
| Warranty registration | 2:37 |
| Claim creation | 2:52 |
| Receipt and document upload | 3:06 |
| OCR extraction | 2:18 |
| Extracted-data verification | 2:29 |
| Data preprocessing | 3:54 |
| Python prediction and confidence for all three classes | 3:54 |
| Claim Summary Card generation | 4:42 |
| Teachable Machine classification and confidences | 4:05 |
| Comparison of both predictions and confidence difference | 4:15 |
| Warranty-rule execution | 4:25 |
| Missing-document detection | 6:25 |
| Contradiction detection | 6:54 |
| Duplicate-claim detection | 6:40 |
| Manual-review routing | 8:15 |
| Reviewer comments or override | 8:35 |
| Administrator dashboard | 10:19 |
| Claim status tracking | 4:58 |
| Report generation | 5:06 |
| One valid claim | 5:35 |
| One invalid claim | 5:45 |
| One manual-review claim | 5:58 |
| One tricky boundary case | 7:34 |
| One model-disagreement case | 7:49 |

## Chapters

| Time | Chapter |
|---|---|
| 0:04 | Title card: Warranty claims, checked twice |
| 0:29 | PART 1 · The live check |
| 1:32 | PART 2 · Customer journey |
| 3:36 | PART 3 · The decision |
| 5:14 | PART 4 · The 11 SRS demonstration cases |
| 8:00 | PART 5 · Manual review (claim reviewer) |
| 8:54 | PART 6 · Service-center desk (service-center staff) |
| 10:03 | PART 7 · Administration (administrator) |
| 11:29 | PART 8 · Beyond the requirements |
| 13:11 | Closing card: Two models. One rulebook. |

## Script

| Time | On screen | Narration |
|---|---|---|
| 0:05 | **Title card: Warranty claims, checked twice** | Hi, and welcome to Assure X, a warranty claim engine built for TechWiz 7. Every claim is checked twice: once by a Python machine learning model, and once by a Google Teachable Machine image model. A configurable warranty policy engine then turns those results into a decision, and whenever the system is unsure, a person decides. |
| 0:30 | **PART 1 · The live check** | Let's start with the landing page, and its live check. |
| 0:37 | The live check runs a real sample claim through the whole pipeline | Right on the home page, this live check runs a real sample claim through the complete pipeline, the same code the product uses. |
| 0:45 | Clean fault: both models say Valid, no rule blocks it, so the claim is Likely Valid | Here's a clean fault. Both models predict Valid Claim, and no warranty rule blocks it, so the recommendation is Likely Valid. |
| 0:57 | Liquid damage: an excluded cause confirmed by a technician gives Likely Invalid | Now liquid damage. That cause is excluded by the policy, and a technician confirmed it, so a hard-fail rule makes it Likely Invalid. |
| 1:08 | Filed four days into the grace period: Uncertain Result, so a person reviews it | And this one was filed four days into the grace period. Confidence drops, the result is uncertain, so the claim goes to a person instead of being auto-decided. |
| 1:22 | Behind the card: two models feed the decision core, the policy engine and the outcome | Behind the card, you can see the flow: the Python model and the vision model feed a decision core, which applies the warranty policy and produces the outcome. |
| 1:33 | **PART 2 · Customer journey** | Part two: the customer journey. We'll register, add a product with O C R, and file a claim from start to finish. |
| 1:44 | User registration: every field is validated in the browser and on the server | First, a new customer creates an account. Every field is validated, both in the browser and again on the server. |
| 1:56 | Sign in with the new account | Now we sign in with the new account. |
| 2:02 | The customer dashboard: products, warranties, claims and pending actions | This is the customer dashboard. Products, warranties, claims, and anything waiting on the customer, all in one place. |
| 2:12 | Product registration: upload the purchase receipt and OCR reads it | To register a product, the customer simply uploads the purchase receipt, and O C R reads it. |
| 2:18 | OCR fills in product, model, serial number, purchase date, price, retailer and invoice number | In a moment, the product name, model, serial number, purchase date, price, retailer and invoice number are all filled in automatically. |
| 2:29 | The customer checks each extracted field before saving | The customer checks each extracted field before anything is saved. |
| 2:37 | The category sets the warranty length: standard or extended cover | The category sets the warranty length, with standard or extended cover. |
| 2:45 | The product and its warranty: coverage dates, status and documents | And here's the registered product, with its warranty coverage dates, status and documents. |
| 2:52 | Claim creation: choose the product | Now let's file a claim. Step one: choose the product. |
| 2:58 | Fault details: category, cause, start date and a description | Step two: the fault. Its category, the cause, when it started, and a short description. |
| 3:06 | Upload the receipt: it is read again and compared with the registered product | Step three: documents. The receipt is read again, and compared with the product on record. |
| 3:14 | OCR check: the serial number on the receipt matches the registered product | The serial number on the receipt matches the registered product, so this check passes. |
| 3:19 | Supporting evidence: warranty card, damage photo and serial-number photo | We add the supporting evidence: the warranty card, a photo of the damage, and a photo of the serial number. |
| 3:29 | Review the claim, then submit | Finally, a quick review, and we submit. |
| 3:37 | **PART 3 · The decision** | Part three: the decision. This is the heart of the system. |
| 3:44 | The verdict: the recommendation, both models and the consistency check | Within a couple of seconds, the claim is decided. At the top is the recommendation, and the time the whole pipeline took. |
| 3:54 | Python model: confidence for Valid, Invalid and Manual Review | On the left is the Python model. The claim's data is pre-processed into features, and the model gives a confidence for each of the three classes. |
| 4:05 | Teachable Machine: classifies the Claim Summary Card, with its own three confidences | On the right is Google Teachable Machine. It classifies an image, the Claim Summary Card, and gives its own three confidences. |
| 4:15 | Comparison: do the classes match, the confidence difference, and the consistency status | In the middle, the two models are compared: do the predicted classes match, how far apart are their confidences, and are they consistent? |
| 4:25 | Why this decision: the warranty rules and the decision-table row that matched | Below that, why this decision. Every warranty rule from the category policy is listed, with the decision table row that matched. |
| 4:35 | What moved the Python model: each input's effect on the prediction | For explainability, this shows which inputs moved the Python model, and by how much. |
| 4:42 | What the image model saw: claim facts only, never a prediction or a decision | And this is exactly what the image model saw. The card shows claim facts only, never a prediction or a decision. The shaded tiles show which parts drove its answer. |
| 4:58 | Claim status tracking: eight stages from filing to closing | The customer can track the claim through eight stages, from filing to closing. |
| 5:06 | Report generation: a PDF with the claim, evidence, both predictions, rules and decision | And with one click, a P D F report is generated, with the claim, the evidence, both predictions, the rules and the decision. |
| 5:15 | **PART 4 · The 11 SRS demonstration cases** | Part four: all eleven demonstration cases from the requirements, each one decided live by the application. |
| 5:35 | Valid claim: both models agree Valid and no rule blocks it: Likely Valid | One. A valid claim. Both models agree it's valid, no rule blocks it, so it's Likely Valid. |
| 5:45 | Invalid claim: an excluded cause confirmed by a technician: Likely Invalid | Two. An invalid claim. Water damage is excluded by the policy, and a technician confirmed it, so a hard-fail rule makes it Likely Invalid. |
| 5:58 | Manual-review claim: the cause is unknown, so a person has to look at it | Three. A manual review claim. The cause is unknown and the diagnosis is inconclusive, so a review rule sends it to a person. |
| 6:11 | Expired warranty: it ended 195 days before the claim, far past the grace period | Four. An expired warranty. The cover ended a hundred and ninety-five days before the claim, far past the seven-day grace period, so it's Likely Invalid. |
| 6:25 | Missing documents: the mandatory receipt is missing, so the claim waits | Five. Missing document detection. The mandatory receipt isn't there, so the claim waits for more information, and the customer is told exactly what's needed. |
| 6:40 | Duplicate detection: the same documents were already used in another claim | Six. Duplicate detection. The same warranty card and invoice were already used in another claim, so this one is flagged as a possible duplicate and sent for review. |
| 6:54 | Contradiction detection: the fault is dated before the purchase date | Seven. Contradiction detection. The fault is dated before the product was even bought, which is impossible, so the claim is routed to review. |
| 7:08 | Serial-number mismatch: the receipt shows a different serial than the registered unit | Eight. A serial number mismatch. The serial on the receipt doesn't match the registered unit, so the claim is Likely Invalid. |
| 7:19 | Unauthorised repair: the unit was repaired at an unauthorised service center | Nine. An unauthorised repair. The repair history shows work by an unauthorised service center, so the policy's hard-fail rule makes it Likely Invalid. |
| 7:34 | Boundary case: filed four days into a seven-day grace period | Ten. A tricky boundary case. It was filed four days into a seven-day grace period. The confidence is low, so the result is uncertain, and a person reviews it. |
| 7:49 | Model disagreement: Python says Invalid, Teachable Machine says Valid, so a person decides | And eleven. A model disagreement. Python says invalid, Teachable Machine says valid. When the models disagree, the system never guesses. A person decides. |
| 8:01 | **PART 5 · Manual review (claim reviewer)** | Part five: manual review. |
| 8:15 | The reviewer queue: filters, risk levels and waiting time | Claims that need a person land in the reviewer's queue, with filters and risk levels. |
| 8:23 | The workbench: evidence, both models' scores and the warranty facts side by side | Let's open the disagreement case. The workbench puts the evidence, both models' scores and the warranty facts side by side. |
| 8:35 | Approve with a written comment, and a written reason for the override | The reviewer approves it, and writes a comment. Because this overrides the automated result, a written reason is required. |
| 8:46 | The decision is recorded, the customer is notified and the status changes | The decision is recorded, the customer is notified, and the claim's status changes. The override is kept in the audit trail. |
| 8:55 | **PART 6 · Service-center desk (service-center staff)** | Part six: the service center desk, the fourth role. |
| 9:08 | Service-center staff: only this center's claims and products, with the customer on every row | Service center staff sign in to their own desk. They see only the claims and products of their service center, with the customer's name on every row. |
| 9:21 | Staff file claims for walk-in customers, with the technician's diagnosis recorded | Staff can file a claim on behalf of a walk-in customer. This one was filed for Usman Tariq by Sana Malik, and the technician's diagnosis and confidence are recorded with it. |
| 9:38 | In the claim form, each product shows its owner, and the diagnostic confidence is required | In the claim form, every product shows its owner. And for staff, the technician's diagnostic confidence is a required field. |
| 9:52 | Staff record repairs; an unauthorised repair is flagged and checked by the warranty rules | Staff also record repairs on the product. This unit was repaired at an unauthorised center, so it's flagged here, and the warranty rules take it into account on every future claim. |
| 10:04 | **PART 7 · Administration (administrator)** | Part seven: administration. |
| 10:19 | Administrator dashboard: claims, automation rate, model agreement and workload | The administrator dashboard shows claim volume, the automation rate, model agreement and the review workload. |
| 10:29 | Charts: claims per week, recommendations, model agreement and confidence | The charts break down claims per week, recommendations, model agreement and confidence. |
| 10:38 | Analytics: frequent faults, rejection reasons, category trends and model evidence | Analytics shows the most frequent faults, the reasons claims are rejected, trends per category, and the evidence for both models. |
| 10:49 | Warranty policies are configuration: coverage, grace periods, exclusions and rule severity | Warranty policies are configuration, not code. Coverage, grace periods, excluded causes and rule severity can all be changed here, with version history. |
| 11:02 | Models: both installed with versions; the Teachable Machine export is uploaded and evaluated here | On the models page, both models are installed with their versions. A new Teachable Machine export can be uploaded and evaluated right here. |
| 11:14 | The audit trail: every login, upload, prediction, decision and override | The audit trail records every login, upload, prediction, decision and override. |
| 11:22 | Access control: roles, record scopes, invitations and blocked attempts | And access control manages roles, which records each role can see, invitations, and blocked attempts. |
| 11:30 | **PART 8 · Beyond the requirements** | Part eight: going beyond the requirements. |
| 11:37 | What-if simulator: try a stricter threshold on 225 stored test decisions | The what-if simulator lets an administrator try a stricter confidence threshold on all 225 stored test decisions, before changing anything. |
| 11:49 | Automation rate, review load and accuracy update instantly; nothing is saved until Apply | Watch the automation rate, the review load and the accuracy update instantly. Nothing is saved until you press apply. |
| 11:59 | Batch evaluation: run uploaded claim records through the real pipeline | Batch evaluation runs a file of claim records through the real pipeline, chunk by chunk. |
| 12:06 | 30 unseen test claims evaluated: accuracy against the labels, with a downloadable CSV | Thirty unseen test claims, evaluated, with accuracy against their labels, and a downloadable C S V. |
| 12:16 | Policy changes are previewed and versioned before they apply | Policy changes are previewed and versioned. And if a change affects a limit shown on the card, the system warns that the image model needs retraining. |
| 12:30 | Input safety: names take no digits and phone numbers take no letters | Input safety: names can't contain digits, and phone numbers can't contain letters. This is enforced in the browser and on the server. |
| 12:41 | Sign-in protection: five wrong passwords pause the account for one minute | Sign-in is protected too. After five wrong passwords, the account is paused for one minute, with a live countdown. |
| 12:52 | The public model card: metrics, confusion matrices and errors for both models | Finally, the public model card. Both models' metrics, confusion matrices and errors, read directly from the evaluation files. |
| 13:03 | The technical blog, also published on Medium | And there's a technical blog explaining how it was built, also published on Medium. |
| 13:12 | **Closing card: Two models. One rulebook.** | The Python model reaches eighty-nine point three percent, and Teachable Machine ninety-three point eight percent, on two hundred and twenty-five unseen test claims. Backed by two hundred and ninety-five automated tests. Two models, one rulebook, and a person whenever it matters. Thank you for watching. |
