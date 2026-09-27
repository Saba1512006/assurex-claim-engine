# Demonstration video — recording script (SRS deliverable 13)

A **.mp4** demonstration video is mandatory. This script covers every item the SRS lists, in an order
that needs no editing. Target length: **12–15 minutes**. Record at 1920×1080 (or 1366×768) with the
browser at 100% zoom; speak over the recording or add captions.

## Before recording (5 minutes)

```
git pull
python database/seed.py        # fresh demo data: 11 SRS cases + a draft
python src/app.py              # http://127.0.0.1:5000
```
Recording tools: **Windows + G** (Xbox Game Bar, records one window) or OBS Studio (free). Save as .mp4.
Keep a receipt PDF ready for the new-claim part: `sample_claims/` or any receipt from
`data/uploads/` (download one from a seeded claim's *Evidence* list).

Logins (all shown on the login page's README too):

| Role | Email | Password |
|---|---|---|
| Customer | `customer@assurex.local` | `CustomerPass123!` |
| Service-center staff | `staff@assurex.local` | `StaffPass123!` |
| Reviewer | `reviewer@assurex.local` | `ReviewerPass123!` |
| Administrator | `admin@assurex.local` | `AdminPass123!` |

## Scenes

| # | Time | Show | SRS items covered |
|---|---|---|---|
| 1 | 0:00 | Landing page; one sentence on the problem; open **Sign in** | — |
| 2 | 0:30 | **Register** a new customer account (name, email, password), then sign in | User registration / login |
| 3 | 1:15 | **Products › Register product**: category, brand, model, serial, purchase date, price, retailer; warranty months; upload the receipt PDF | Product registration, warranty registration, receipt upload |
| 4 | 2:15 | The receipt's **extracted details** (invoice no., date, serial, retailer, amount): correct one value and save | OCR extraction, extracted-data verification |
| 5 | 3:00 | **New claim** wizard: pick the product → fault, damage cause, fault date → upload damage + serial photos → review. Point at the live readiness checklist | Claim creation, document upload, missing-document detection |
| 6 | 4:00 | **Submit**. On the claim page: features used (preprocessing), **Python prediction with all three confidences**, the **Claim Summary Card**, **Teachable Machine prediction with all three confidences**, class match, **confidence difference** and consistency status | Data preprocessing, Python prediction + confidences, card generation, Teachable Machine classification + confidences, comparison, confidence difference |
| 7 | 5:15 | Scroll: **warranty rules** (16 checks, pass/fail with reasons), contradictions, duplicate indicators, the decision table row that fired | Warranty-rule execution |
| 8 | 6:00 | Sign in as `customer@assurex.local`. Open **ApexBook Pro 16** (Likely Valid, both models agree) | One valid claim |
| 9 | 6:30 | Open **FrostGuard 450L** (water ingress excluded → Likely Invalid) and **NovaPhone 12** (expired warranty) | One invalid claim, expired warranty |
| 10 | 7:15 | Open **VoltEdge Saw 18V** (unknown cause → manual review) and **CleanCycle 8kg** (no receipt → missing mandatory document) | Manual-review claim, missing document |
| 11 | 8:00 | **VividTab 11**: fault dated before purchase → contradiction. **ApexBook Pro 16** filed by Kamran: reused receipt/invoice → duplicate. **IronForge Grinder 9**: receipt serial ≠ registered serial | Contradiction, duplicate, serial mismatch |
| 12 | 9:00 | **AeroBreeze 1.5T**: repair at an unauthorised shop → Likely Invalid. **NovaPods Max**: warranty ended 4 days ago, inside the grace period → routed to review | Unauthorised repair, tricky boundary date |
| 13 | 9:45 | **KitchenPro Oven 45L** (Kamran): reported 35 days after the fault; Home Appliances allow 45. Teachable Machine says *Valid* (95%) — its card shows "Reported in time"; the Python model says *Invalid* (91%) — it mostly learned 30-day limits. → *Model Disagreement* → Manual Review Required (rule D04) | Model-disagreement case |
| 14 | 10:30 | Sign in as **reviewer**: **Review queue** → take a claim → add a comment, **override** with a written reason → decision saved | Manual-review routing, reviewer comments / override |
| 15 | 11:30 | Sign in as **customer**: claim **Track** page (8 stages, timeline, notification) | Claim status tracking |
| 16 | 12:00 | Claim page › **Report (PDF)** — open the downloaded report | Report generation |
| 17 | 12:30 | Sign in as **admin**: **Overview** dashboard (totals, decisions, disagreements), **Analytics** (both models' accuracy, confusion matrices), **Models** (Python 89.3%, Teachable Machine 93.8%), **Policies** (edit a rule), **Audit** | Administrator dashboard |
| 18 | 14:00 | Close: GitHub link and blog link on screen | — |

## Tips

* Open each claim in the same browser tab so the recording stays smooth; zoom out (Ctrl + −) if a page
  is long rather than scrolling fast.
* Say the claim's product name aloud before explaining it, so the evaluator can match it to this table.
* After recording, upload the .mp4 (YouTube *unlisted* or Google Drive with link sharing) and put the link
  in `README.md` under **Links → Demonstration video**.
