# Publishing the technical blog on Medium

`medium_article.html` is the current `documentation/TECHNICAL_BLOG.md`, prepared for Medium's editor
(no tables, image placeholders, headings Medium keeps on paste). Rebuild it after editing the blog:
`python documentation/medium/build_medium.py`.

## Steps

1. Open `medium_article.html` in Chrome (double-click it).
2. Press **Ctrl+A**, then **Ctrl+C**.
3. On medium.com: **Write** → click in the empty story → **Ctrl+V**.
4. Delete the blue note at the very top.
5. For each yellow box: click an empty line where it is, press the **+** button → **image icon** → choose
   the file named in the box from `documentation/medium/images/`, type the caption under the image, then
   delete the yellow box.
6. Check that the title shows as the story title and the grey line under it as the subtitle.
7. **Publish** → add the tags below → **Publish now**.
8. Copy the new story's link into `documentation/BLOG_PUBLICATION.md` (and the old story can be unlisted).

## Story settings

| Field | Value |
|---|---|
| Title | Building AssureX: two models, one rulebook, and why our first 100% was a bug |
| Subtitle | How we built a warranty-claim engine that combines a Python classifier, a Google Teachable Machine image model and a configurable rule engine — and what we learned when our first version scored suspiciously well. |
| Tags (max 5) | Machine Learning · Python · Teachable Machine · Data Science · Flask |
| Preview image | `images/02_card_v2_vs_v3.png` |

## Images

| # | File | Goes after the section |
|---|---|---|
| 1 | `images/01_architecture.png` | Application architecture |
| 2 | `images/02_card_v2_vs_v3.png` | Google Teachable Machine training and the Claim Summary Card |
| 3 | `images/03_claim_page.jpg` | Confidence-score comparison |
| 4 | `images/04_model_evaluation.png` | Model disagreement cases |
| 5 | `images/05_decision_flow.png` | Warranty-rule design |
