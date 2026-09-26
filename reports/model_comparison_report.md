# Model prediction & confidence comparison — test split

225 unseen claims. Python model on the structured record; Google Teachable Machine on the claim's canonical Claim Summary Card; rules and decision table as in production.

> **Teachable Machine model not installed.** Its columns read “unavailable”, every comparison is *Uncertain Result*, and the application sends those claims to manual review. Install the export (Admin › Models) and re-run this script to fill the columns.

## Overall comparison summary

| Metric | Value |
|---|---|
| Python model accuracy | 89.3% |
| Python model macro F1 | 89.2% |
| Application decision accuracy (decision → class) | 64.0% |

**Consistency statuses:** Uncertain Result 225

**Final decisions:** Manual Review Required 155, Likely Invalid 70

## Major disagreements

- Not measurable until the Teachable Machine model is installed.

## Per-claim results

| Claim ID | Actual class | Python predicted class | Python conf. Valid | Python conf. Invalid | Python conf. Manual | Card filename | GTM predicted class | GTM conf. Valid | GTM conf. Invalid | GTM conf. Manual | Classes match | Top-confidence difference | Consistency status | Warranty-rule result | Missing documents | Contradictions | Duplicate indicators | Final application decision | Explanation of disagreement |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CLM-01428 | Manual Review | Manual Review | 0.0200 | 0.0393 | 0.9407 | CLM-01428_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00367 | Valid Claim | Valid Claim | 0.7903 | 0.0957 | 0.1140 | CLM-00367_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00654 | Valid Claim | Valid Claim | 0.7300 | 0.0355 | 0.2345 | CLM-00654_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00539 | Invalid Claim | Invalid Claim | 0.0119 | 0.8961 | 0.0920 | CLM-00539_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-00816 | Manual Review | Manual Review | 0.0271 | 0.2208 | 0.7521 | CLM-00816_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01383 | Valid Claim | Valid Claim | 0.8138 | 0.0412 | 0.1449 | CLM-01383_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00508 | Valid Claim | Valid Claim | 0.6899 | 0.0157 | 0.2943 | CLM-00508_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00850 | Valid Claim | Valid Claim | 0.8673 | 0.0182 | 0.1145 | CLM-00850_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00535 | Invalid Claim | Invalid Claim | 0.0478 | 0.8358 | 0.1165 | CLM-00535_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice; Warranty card; Damage / fault photo | — | — | Likely Invalid | — |
| CLM-00988 | Invalid Claim | Valid Claim | 0.9376 | 0.0305 | 0.0319 | CLM-00988_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00458 | Manual Review | Manual Review | 0.0167 | 0.0853 | 0.8981 | CLM-00458_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00266 | Manual Review | Manual Review | 0.1796 | 0.0710 | 0.7494 | CLM-00266_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00159 | Valid Claim | Valid Claim | 0.8131 | 0.0949 | 0.0919 | CLM-00159_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00925 | Invalid Claim | Invalid Claim | 0.0123 | 0.8131 | 0.1746 | CLM-00925_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | — | — | Likely Invalid | — |
| CLM-01117 | Valid Claim | Valid Claim | 0.7763 | 0.0452 | 0.1785 | CLM-01117_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01444 | Invalid Claim | Invalid Claim | 0.0244 | 0.8322 | 0.1434 | CLM-01444_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01196 | Valid Claim | Valid Claim | 0.7772 | 0.0127 | 0.2102 | CLM-01196_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01441 | Invalid Claim | Invalid Claim | 0.0086 | 0.7925 | 0.1989 | CLM-01441_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo; Damage / fault photo | — | — | Likely Invalid | — |
| CLM-00906 | Valid Claim | Valid Claim | 0.8365 | 0.0215 | 0.1420 | CLM-00906_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00627 | Invalid Claim | Invalid Claim | 0.0055 | 0.9561 | 0.0385 | CLM-00627_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00016 | Manual Review | Manual Review | 0.0064 | 0.3826 | 0.6110 | CLM-00016_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01154 | Valid Claim | Valid Claim | 0.9429 | 0.0238 | 0.0333 | CLM-01154_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00104 | Manual Review | Manual Review | 0.1524 | 0.0086 | 0.8391 | CLM-00104_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00066 | Valid Claim | Valid Claim | 0.7844 | 0.0144 | 0.2011 | CLM-00066_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00078 | Invalid Claim | Invalid Claim | 0.0369 | 0.9013 | 0.0618 | CLM-00078_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01425 | Invalid Claim | Invalid Claim | 0.0167 | 0.9616 | 0.0218 | CLM-01425_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01421 | Valid Claim | Valid Claim | 0.9415 | 0.0185 | 0.0401 | CLM-01421_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00050 | Invalid Claim | Invalid Claim | 0.0287 | 0.8274 | 0.1439 | CLM-00050_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00003 | Valid Claim | Valid Claim | 0.9150 | 0.0172 | 0.0677 | CLM-00003_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00777 | Manual Review | Manual Review | 0.0077 | 0.0510 | 0.9413 | CLM-00777_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | Invoice number reused | Manual Review Required | — |
| CLM-00042 | Valid Claim | Valid Claim | 0.8091 | 0.0202 | 0.1707 | CLM-00042_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00253 | Manual Review | Manual Review | 0.2888 | 0.2326 | 0.4786 | CLM-00253_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00008 | Invalid Claim | Invalid Claim | 0.0064 | 0.7535 | 0.2401 | CLM-00008_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Fault/claim dates conflict with the purchase date | — | Likely Invalid | — |
| CLM-01275 | Manual Review | Manual Review | 0.0110 | 0.2052 | 0.7837 | CLM-01275_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00398 | Manual Review | Manual Review | 0.0134 | 0.0180 | 0.9686 | CLM-00398_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Warranty card | — | — | Manual Review Required | — |
| CLM-01418 | Invalid Claim | Invalid Claim | 0.0332 | 0.8244 | 0.1423 | CLM-01418_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00106 | Valid Claim | Invalid Claim | 0.2562 | 0.6611 | 0.0827 | CLM-00106_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00503 | Invalid Claim | Invalid Claim | 0.0109 | 0.7269 | 0.2623 | CLM-00503_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Warranty card | — | — | Likely Invalid | — |
| CLM-00793 | Invalid Claim | Invalid Claim | 0.0073 | 0.8268 | 0.1658 | CLM-00793_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Warranty card | — | — | Likely Invalid | — |
| CLM-00989 | Invalid Claim | Invalid Claim | 0.0064 | 0.8160 | 0.1777 | CLM-00989_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00707 | Valid Claim | Valid Claim | 0.8232 | 0.0178 | 0.1590 | CLM-00707_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00033 | Manual Review | Manual Review | 0.0486 | 0.0466 | 0.9048 | CLM-00033_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00433 | Valid Claim | Invalid Claim | 0.1035 | 0.8424 | 0.0541 | CLM-00433_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01222 | Manual Review | Manual Review | 0.0366 | 0.2411 | 0.7223 | CLM-01222_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00396 | Invalid Claim | Invalid Claim | 0.0129 | 0.8090 | 0.1780 | CLM-00396_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Warranty card | — | Invoice number reused | Likely Invalid | — |
| CLM-00962 | Valid Claim | Valid Claim | 0.6077 | 0.0366 | 0.3556 | CLM-00962_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00966 | Invalid Claim | Invalid Claim | 0.0586 | 0.9275 | 0.0139 | CLM-00966_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01022 | Valid Claim | Valid Claim | 0.9544 | 0.0207 | 0.0249 | CLM-01022_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00811 | Valid Claim | Valid Claim | 0.8688 | 0.0286 | 0.1026 | CLM-00811_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00228 | Valid Claim | Valid Claim | 0.6585 | 0.0420 | 0.2994 | CLM-00228_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01180 | Invalid Claim | Invalid Claim | 0.0079 | 0.6804 | 0.3117 | CLM-01180_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | Fault/claim dates conflict with the purchase date | — | Likely Invalid | — |
| CLM-00410 | Manual Review | Manual Review | 0.0588 | 0.0354 | 0.9058 | CLM-00410_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00588 | Manual Review | Manual Review | 0.0431 | 0.0066 | 0.9504 | CLM-00588_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-01103 | Invalid Claim | Invalid Claim | 0.0392 | 0.8685 | 0.0923 | CLM-01103_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice | — | — | Likely Invalid | — |
| CLM-00097 | Valid Claim | Valid Claim | 0.9155 | 0.0229 | 0.0616 | CLM-00097_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00784 | Valid Claim | Valid Claim | 0.8462 | 0.0530 | 0.1008 | CLM-00784_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00009 | Manual Review | Manual Review | 0.0350 | 0.0287 | 0.9363 | CLM-00009_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00120 | Manual Review | Valid Claim | 0.8610 | 0.0403 | 0.0987 | CLM-00120_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00519 | Manual Review | Manual Review | 0.1123 | 0.2545 | 0.6333 | CLM-00519_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-01371 | Invalid Claim | Invalid Claim | 0.0122 | 0.8913 | 0.0965 | CLM-01371_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice | — | — | Likely Invalid | — |
| CLM-00127 | Manual Review | Manual Review | 0.0492 | 0.0322 | 0.9186 | CLM-00127_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-01254 | Manual Review | Valid Claim | 0.7610 | 0.0059 | 0.2332 | CLM-01254_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00683 | Valid Claim | Valid Claim | 0.6741 | 0.0600 | 0.2660 | CLM-00683_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01460 | Invalid Claim | Valid Claim | 0.6715 | 0.0371 | 0.2915 | CLM-01460_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00868 | Manual Review | Manual Review | 0.0491 | 0.3413 | 0.6096 | CLM-00868_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-01340 | Invalid Claim | Invalid Claim | 0.0030 | 0.9580 | 0.0391 | CLM-01340_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00833 | Invalid Claim | Invalid Claim | 0.0033 | 0.7248 | 0.2718 | CLM-00833_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | Invoice number reused | Likely Invalid | — |
| CLM-01127 | Manual Review | Manual Review | 0.0207 | 0.1295 | 0.8498 | CLM-01127_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00942 | Valid Claim | Valid Claim | 0.8968 | 0.0848 | 0.0185 | CLM-00942_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01215 | Valid Claim | Valid Claim | 0.9369 | 0.0392 | 0.0239 | CLM-01215_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00875 | Valid Claim | Valid Claim | 0.8632 | 0.0378 | 0.0990 | CLM-00875_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01447 | Valid Claim | Valid Claim | 0.8619 | 0.0204 | 0.1177 | CLM-01447_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00785 | Invalid Claim | Invalid Claim | 0.0294 | 0.9235 | 0.0471 | CLM-00785_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00021 | Manual Review | Manual Review | 0.0212 | 0.0161 | 0.9626 | CLM-00021_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00643 | Invalid Claim | Invalid Claim | 0.0239 | 0.8846 | 0.0914 | CLM-00643_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01432 | Manual Review | Manual Review | 0.0094 | 0.0666 | 0.9240 | CLM-01432_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-01370 | Invalid Claim | Manual Review | 0.0167 | 0.2933 | 0.6899 | CLM-01370_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00703 | Valid Claim | Valid Claim | 0.9027 | 0.0128 | 0.0845 | CLM-00703_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01341 | Invalid Claim | Invalid Claim | 0.0109 | 0.9658 | 0.0233 | CLM-01341_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00309 | Invalid Claim | Manual Review | 0.0279 | 0.2181 | 0.7540 | CLM-00309_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01191 | Manual Review | Valid Claim | 0.9531 | 0.0278 | 0.0191 | CLM-01191_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01347 | Invalid Claim | Invalid Claim | 0.0149 | 0.9429 | 0.0422 | CLM-01347_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01188 | Valid Claim | Valid Claim | 0.9140 | 0.0537 | 0.0323 | CLM-01188_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00701 | Valid Claim | Valid Claim | 0.8149 | 0.0232 | 0.1618 | CLM-00701_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00880 | Valid Claim | Valid Claim | 0.6788 | 0.0050 | 0.3162 | CLM-00880_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01437 | Manual Review | Manual Review | 0.0110 | 0.0973 | 0.8917 | CLM-01437_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00582 | Invalid Claim | Invalid Claim | 0.0373 | 0.8751 | 0.0876 | CLM-00582_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01150 | Invalid Claim | Invalid Claim | 0.0296 | 0.9015 | 0.0689 | CLM-01150_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00151 | Manual Review | Manual Review | 0.0119 | 0.0373 | 0.9508 | CLM-00151_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-01131 | Valid Claim | Valid Claim | 0.7014 | 0.0089 | 0.2897 | CLM-01131_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00428 | Valid Claim | Valid Claim | 0.9049 | 0.0688 | 0.0263 | CLM-00428_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00919 | Invalid Claim | Invalid Claim | 0.0341 | 0.9487 | 0.0172 | CLM-00919_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00191 | Invalid Claim | Invalid Claim | 0.0109 | 0.9324 | 0.0567 | CLM-00191_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Warranty card | — | — | Likely Invalid | — |
| CLM-00152 | Manual Review | Manual Review | 0.0250 | 0.0378 | 0.9372 | CLM-00152_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Serial-number photo | — | — | Manual Review Required | — |
| CLM-00808 | Manual Review | Manual Review | 0.0039 | 0.0206 | 0.9755 | CLM-00808_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-00402 | Valid Claim | Valid Claim | 0.9337 | 0.0437 | 0.0226 | CLM-00402_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00901 | Valid Claim | Valid Claim | 0.7678 | 0.1059 | 0.1264 | CLM-00901_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00411 | Manual Review | Manual Review | 0.0231 | 0.0299 | 0.9470 | CLM-00411_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00721 | Invalid Claim | Invalid Claim | 0.0214 | 0.9025 | 0.0762 | CLM-00721_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Fault/claim dates conflict with the purchase date | — | Likely Invalid | — |
| CLM-00864 | Manual Review | Manual Review | 0.0040 | 0.0669 | 0.9291 | CLM-00864_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00853 | Manual Review | Manual Review | 0.0436 | 0.1014 | 0.8551 | CLM-00853_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00285 | Valid Claim | Valid Claim | 0.7228 | 0.1820 | 0.0952 | CLM-00285_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01237 | Valid Claim | Valid Claim | 0.9174 | 0.0307 | 0.0520 | CLM-01237_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-00040 | Valid Claim | Valid Claim | 0.8631 | 0.0368 | 0.1000 | CLM-00040_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00197 | Invalid Claim | Invalid Claim | 0.0453 | 0.8785 | 0.0762 | CLM-00197_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | Invoice number reused | Likely Invalid | — |
| CLM-00189 | Manual Review | Invalid Claim | 0.0043 | 0.5063 | 0.4894 | CLM-00189_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00333 | Manual Review | Manual Review | 0.0094 | 0.2338 | 0.7568 | CLM-00333_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01419 | Valid Claim | Valid Claim | 0.5412 | 0.0093 | 0.4495 | CLM-01419_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00883 | Invalid Claim | Valid Claim | 0.9004 | 0.0621 | 0.0375 | CLM-00883_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00490 | Invalid Claim | Invalid Claim | 0.0468 | 0.8877 | 0.0656 | CLM-00490_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00517 | Valid Claim | Invalid Claim | 0.1215 | 0.6299 | 0.2486 | CLM-00517_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00438 | Valid Claim | Valid Claim | 0.9282 | 0.0221 | 0.0497 | CLM-00438_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00473 | Valid Claim | Valid Claim | 0.8254 | 0.0128 | 0.1618 | CLM-00473_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01054 | Invalid Claim | Invalid Claim | 0.2166 | 0.7590 | 0.0244 | CLM-01054_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-00203 | Valid Claim | Valid Claim | 0.8785 | 0.0744 | 0.0471 | CLM-00203_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01323 | Manual Review | Manual Review | 0.0801 | 0.0119 | 0.9080 | CLM-01323_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-00714 | Manual Review | Manual Review | 0.0089 | 0.1668 | 0.8243 | CLM-00714_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-01346 | Manual Review | Manual Review | 0.0333 | 0.3697 | 0.5971 | CLM-01346_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00538 | Manual Review | Manual Review | 0.0078 | 0.2711 | 0.7210 | CLM-00538_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00221 | Manual Review | Manual Review | 0.0488 | 0.0430 | 0.9082 | CLM-00221_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00723 | Manual Review | Manual Review | 0.0752 | 0.0239 | 0.9009 | CLM-00723_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | Invoice number reused | Manual Review Required | — |
| CLM-00095 | Manual Review | Manual Review | 0.0142 | 0.1913 | 0.7944 | CLM-00095_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00546 | Manual Review | Valid Claim | 0.9124 | 0.0458 | 0.0418 | CLM-00546_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01489 | Manual Review | Manual Review | 0.0396 | 0.1331 | 0.8273 | CLM-01489_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00954 | Invalid Claim | Invalid Claim | 0.0612 | 0.9080 | 0.0308 | CLM-00954_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01066 | Manual Review | Manual Review | 0.0925 | 0.1002 | 0.8073 | CLM-01066_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Serial-number photo | — | — | Manual Review Required | — |
| CLM-01128 | Valid Claim | Valid Claim | 0.9376 | 0.0242 | 0.0381 | CLM-01128_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01230 | Valid Claim | Valid Claim | 0.9365 | 0.0172 | 0.0463 | CLM-01230_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01138 | Manual Review | Manual Review | 0.0033 | 0.1591 | 0.8375 | CLM-01138_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | Fault/claim dates conflict with the purchase date | Invoice number reused | Manual Review Required | — |
| CLM-00395 | Manual Review | Manual Review | 0.0187 | 0.1533 | 0.8280 | CLM-00395_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Serial-number photo | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-00960 | Valid Claim | Valid Claim | 0.8730 | 0.0272 | 0.0998 | CLM-00960_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00417 | Valid Claim | Valid Claim | 0.8639 | 0.0591 | 0.0770 | CLM-00417_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00216 | Valid Claim | Valid Claim | 0.8307 | 0.1198 | 0.0496 | CLM-00216_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00371 | Valid Claim | Valid Claim | 0.8709 | 0.1131 | 0.0160 | CLM-00371_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00419 | Invalid Claim | Invalid Claim | 0.0431 | 0.9146 | 0.0423 | CLM-00419_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00280 | Manual Review | Manual Review | 0.0263 | 0.0154 | 0.9583 | CLM-00280_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice; Serial-number photo | — | — | Manual Review Required | — |
| CLM-00778 | Invalid Claim | Invalid Claim | 0.0014 | 0.5392 | 0.4594 | CLM-00778_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01158 | Invalid Claim | Invalid Claim | 0.0686 | 0.9214 | 0.0100 | CLM-01158_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00809 | Valid Claim | Valid Claim | 0.7257 | 0.1346 | 0.1397 | CLM-00809_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | — | — | Likely Invalid | — |
| CLM-01177 | Valid Claim | Valid Claim | 0.9254 | 0.0376 | 0.0369 | CLM-01177_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01053 | Manual Review | Manual Review | 0.0097 | 0.0544 | 0.9359 | CLM-01053_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01313 | Invalid Claim | Manual Review | 0.0023 | 0.3065 | 0.6913 | CLM-01313_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01189 | Valid Claim | Valid Claim | 0.6525 | 0.0248 | 0.3226 | CLM-01189_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01456 | Invalid Claim | Manual Review | 0.0026 | 0.4478 | 0.5496 | CLM-01456_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | — | — | Likely Invalid | — |
| CLM-01273 | Invalid Claim | Invalid Claim | 0.1702 | 0.7771 | 0.0527 | CLM-01273_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00233 | Invalid Claim | Invalid Claim | 0.0338 | 0.8523 | 0.1139 | CLM-00233_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01430 | Manual Review | Manual Review | 0.0182 | 0.0107 | 0.9710 | CLM-01430_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00757 | Valid Claim | Valid Claim | 0.8718 | 0.0082 | 0.1201 | CLM-00757_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00857 | Valid Claim | Valid Claim | 0.8432 | 0.0626 | 0.0942 | CLM-00857_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00346 | Invalid Claim | Invalid Claim | 0.1990 | 0.7904 | 0.0106 | CLM-00346_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00618 | Invalid Claim | Valid Claim | 0.9347 | 0.0289 | 0.0364 | CLM-00618_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00432 | Valid Claim | Valid Claim | 0.9422 | 0.0113 | 0.0465 | CLM-00432_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01414 | Manual Review | Manual Review | 0.0606 | 0.0912 | 0.8482 | CLM-01414_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00791 | Invalid Claim | Manual Review | 0.0041 | 0.0177 | 0.9783 | CLM-00791_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00632 | Invalid Claim | Manual Review | 0.0209 | 0.1130 | 0.8661 | CLM-00632_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice; Warranty card | — | — | Likely Invalid | — |
| CLM-01367 | Manual Review | Manual Review | 0.0307 | 0.0090 | 0.9603 | CLM-01367_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01498 | Invalid Claim | Invalid Claim | 0.0152 | 0.9169 | 0.0679 | CLM-01498_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01259 | Invalid Claim | Invalid Claim | 0.0175 | 0.9399 | 0.0426 | CLM-01259_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00909 | Invalid Claim | Invalid Claim | 0.0188 | 0.7737 | 0.2075 | CLM-00909_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-01003 | Manual Review | Manual Review | 0.0251 | 0.0348 | 0.9400 | CLM-01003_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01457 | Manual Review | Manual Review | 0.3076 | 0.0159 | 0.6766 | CLM-01457_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00319 | Valid Claim | Valid Claim | 0.8574 | 0.0775 | 0.0650 | CLM-00319_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-00600 | Valid Claim | Valid Claim | 0.8441 | 0.0334 | 0.1225 | CLM-00600_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-01219 | Manual Review | Manual Review | 0.1680 | 0.0519 | 0.7801 | CLM-01219_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Serial-number photo | — | — | Manual Review Required | — |
| CLM-00347 | Valid Claim | Valid Claim | 0.8891 | 0.0314 | 0.0794 | CLM-00347_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01040 | Invalid Claim | Valid Claim | 0.4506 | 0.2513 | 0.2981 | CLM-01040_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Damage / fault photo | — | — | Likely Invalid | — |
| CLM-00169 | Invalid Claim | Invalid Claim | 0.0034 | 0.6862 | 0.3104 | CLM-00169_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00187 | Invalid Claim | Invalid Claim | 0.0039 | 0.9416 | 0.0544 | CLM-00187_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01025 | Manual Review | Manual Review | 0.3239 | 0.0255 | 0.6506 | CLM-01025_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00646 | Manual Review | Manual Review | 0.0178 | 0.4668 | 0.5155 | CLM-00646_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00663 | Manual Review | Manual Review | 0.0942 | 0.0941 | 0.8118 | CLM-00663_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-00994 | Invalid Claim | Invalid Claim | 0.2771 | 0.6945 | 0.0284 | CLM-00994_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01377 | Invalid Claim | Invalid Claim | 0.0079 | 0.9508 | 0.0414 | CLM-01377_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00278 | Manual Review | Manual Review | 0.0756 | 0.0680 | 0.8564 | CLM-00278_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-01096 | Manual Review | Manual Review | 0.0550 | 0.0102 | 0.9348 | CLM-01096_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-01140 | Manual Review | Manual Review | 0.0149 | 0.4759 | 0.5092 | CLM-01140_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01303 | Manual Review | Manual Review | 0.0126 | 0.1457 | 0.8417 | CLM-01303_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00205 | Manual Review | Manual Review | 0.1146 | 0.2112 | 0.6742 | CLM-00205_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | Fault/claim dates conflict with the purchase date | — | Manual Review Required | — |
| CLM-01248 | Valid Claim | Valid Claim | 0.7534 | 0.2222 | 0.0244 | CLM-01248_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-00161 | Valid Claim | Valid Claim | 0.8753 | 0.0844 | 0.0403 | CLM-00161_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00435 | Invalid Claim | Invalid Claim | 0.0474 | 0.7974 | 0.1552 | CLM-00435_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00645 | Invalid Claim | Invalid Claim | 0.0431 | 0.9190 | 0.0378 | CLM-00645_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01359 | Manual Review | Manual Review | 0.0175 | 0.0196 | 0.9629 | CLM-01359_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00586 | Invalid Claim | Invalid Claim | 0.1238 | 0.7989 | 0.0773 | CLM-00586_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00339 | Invalid Claim | Invalid Claim | 0.0384 | 0.9453 | 0.0163 | CLM-00339_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01396 | Manual Review | Manual Review | 0.1109 | 0.1151 | 0.7740 | CLM-01396_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Serial-number photo | — | — | Manual Review Required | — |
| CLM-00702 | Invalid Claim | Invalid Claim | 0.0071 | 0.7503 | 0.2426 | CLM-00702_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Warranty card | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00482 | Valid Claim | Valid Claim | 0.6905 | 0.0043 | 0.3052 | CLM-00482_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-00129 | Manual Review | Manual Review | 0.0173 | 0.0198 | 0.9629 | CLM-00129_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Damage / fault photo | — | Invoice number reused | Manual Review Required | — |
| CLM-01042 | Invalid Claim | Invalid Claim | 0.0163 | 0.6492 | 0.3345 | CLM-01042_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-00762 | Manual Review | Manual Review | 0.2311 | 0.0568 | 0.7121 | CLM-00762_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Damage / fault photo | — | — | Manual Review Required | — |
| CLM-01330 | Invalid Claim | Manual Review | 0.0117 | 0.2891 | 0.6992 | CLM-01330_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice | — | — | Likely Invalid | — |
| CLM-01181 | Manual Review | Manual Review | 0.0195 | 0.0187 | 0.9617 | CLM-01181_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-00755 | Invalid Claim | Invalid Claim | 0.0100 | 0.9050 | 0.0849 | CLM-00755_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01217 | Manual Review | Manual Review | 0.0515 | 0.1315 | 0.8169 | CLM-01217_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Serial-number photo | — | — | Manual Review Required | — |
| CLM-00061 | Invalid Claim | Invalid Claim | 0.1181 | 0.8487 | 0.0332 | CLM-00061_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-01479 | Invalid Claim | Valid Claim | 0.6031 | 0.1399 | 0.2570 | CLM-01479_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-00807 | Invalid Claim | Invalid Claim | 0.0070 | 0.5320 | 0.4610 | CLM-00807_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01382 | Valid Claim | Valid Claim | 0.9409 | 0.0345 | 0.0245 | CLM-01382_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00770 | Valid Claim | Manual Review | 0.0061 | 0.0833 | 0.9106 | CLM-00770_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00897 | Invalid Claim | Invalid Claim | 0.0111 | 0.9024 | 0.0865 | CLM-00897_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Purchase receipt / invoice | — | — | Likely Invalid | — |
| CLM-01141 | Valid Claim | Valid Claim | 0.7787 | 0.1499 | 0.0714 | CLM-01141_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00269 | Manual Review | Manual Review | 0.0059 | 0.0055 | 0.9886 | CLM-00269_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00621 | Manual Review | Manual Review | 0.4530 | 0.0247 | 0.5223 | CLM-00621_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-01262 | Manual Review | Manual Review | 0.0160 | 0.0786 | 0.9054 | CLM-01262_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card | — | — | Manual Review Required | — |
| CLM-00077 | Invalid Claim | Manual Review | 0.0128 | 0.3684 | 0.6189 | CLM-00077_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00222 | Invalid Claim | Invalid Claim | 0.0875 | 0.8729 | 0.0397 | CLM-00222_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | — | — | Likely Invalid | — |
| CLM-00623 | Manual Review | Manual Review | 0.0071 | 0.1071 | 0.8857 | CLM-00623_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01122 | Valid Claim | Valid Claim | 0.8920 | 0.0104 | 0.0976 | CLM-01122_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-01471 | Valid Claim | Valid Claim | 0.9340 | 0.0190 | 0.0470 | CLM-01471_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00262 | Valid Claim | Valid Claim | 0.6612 | 0.0953 | 0.2435 | CLM-00262_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00046 | Valid Claim | Valid Claim | 0.9236 | 0.0309 | 0.0455 | CLM-00046_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01198 | Manual Review | Manual Review | 0.0487 | 0.0736 | 0.8777 | CLM-01198_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | — | — | — | Manual Review Required | — |
| CLM-00597 | Valid Claim | Valid Claim | 0.9084 | 0.0629 | 0.0287 | CLM-00597_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00970 | Valid Claim | Valid Claim | 0.7836 | 0.1387 | 0.0777 | CLM-00970_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00936 | Valid Claim | Valid Claim | 0.8670 | 0.0858 | 0.0472 | CLM-00936_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-00442 | Invalid Claim | Invalid Claim | 0.0301 | 0.5480 | 0.4219 | CLM-00442_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-01474 | Manual Review | Invalid Claim | 0.0383 | 0.5708 | 0.3909 | CLM-01474_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00195 | Invalid Claim | Invalid Claim | 0.2259 | 0.7569 | 0.0172 | CLM-00195_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | Serial-number photo | — | — | Likely Invalid | — |
| CLM-01492 | Valid Claim | Valid Claim | 0.9392 | 0.0201 | 0.0407 | CLM-01492_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
| CLM-01398 | Invalid Claim | Invalid Claim | 0.0041 | 0.9672 | 0.0287 | CLM-01398_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | FAIL | — | Serial number does not match the evidence | — | Likely Invalid | — |
| CLM-00971 | Valid Claim | Valid Claim | 0.8002 | 0.0234 | 0.1765 | CLM-00971_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Serial-number photo | — | — | Manual Review Required | — |
| CLM-00312 | Manual Review | Manual Review | 0.1459 | 0.0162 | 0.8379 | CLM-00312_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Purchase receipt / invoice | — | — | Manual Review Required | — |
| CLM-00647 | Manual Review | Manual Review | 0.1421 | 0.0246 | 0.8333 | CLM-00647_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | REVIEW | Warranty card; Damage / fault photo | — | — | Manual Review Required | — |
| CLM-01013 | Valid Claim | Valid Claim | 0.9355 | 0.0327 | 0.0319 | CLM-01013_v0.jpg | unavailable | — | — | — | — | — | Uncertain Result | PASS | — | — | — | Manual Review Required | — |
