# Screening Methodology

## Document type and fields

Type detection counts known visible keywords in the OCR transcript and filename. Its confidence is a heuristic evidence estimate, not a calibrated model probability. Field extraction accepts labeled lines and conservative ID patterns; it does not infer an absent value.

## Validation and registry

Required fields vary by document type. Recognized dates are normalized where possible, expiry is checked against the local date, and trusted-record fields are compared after case/whitespace normalization. Unavailable OCR or registry data is surfaced as unavailable/warning and must not be interpreted as a pass or proof of fraud.

## MRZ

When two 44-character TD3 lines appear, the service checks passport number, date of birth, expiry, and composite check digits. It also compares visible name/document-number values where available. Other MRZ formats currently return `NOT_AVAILABLE`.

## Possible manipulation indicators

The MVP recompresses the image and measures an ELA-style difference, regional variance, and median-filter residual spread. It reports low/medium/high indication and candidate grid regions. These signals are sensitive to ordinary camera, scanner, resize, and compression changes. They do not prove alteration and require manual review.

## Optional face comparison

InsightFace uses CPU face detection and ArcFace-style embeddings when installed. The service compares cosine similarity against a configured fictional reference image using a demo threshold of 0.40. This threshold is not calibrated for identity decisions. Missing runtime, image, or face returns an unavailable status and does not raise risk as a mismatch.

## Explainable score

| Factor | Maximum points |
| --- | ---: |
| Field mismatches | 40 |
| Additional validation failures | 15 |
| Revoked/blacklisted/expired status | 15 |
| Failed expiry validation | 8 |
| Inconsistent MRZ | 15 |
| Possible manipulation indicators | 20 |
| Face mismatch | 15 |
| Trusted reference missing | 5 |
| Low OCR confidence | 8 |

Each independent mismatch contributes points: a single minor mismatch starts at 25, a critical name/document-number mismatch starts at 30, and additional fields add 5 points up to the 40-point factor cap. Other validation failures add 5 points each up to 15. Revoked/blacklisted records add 15; expired status adds 10, and a failed expiry-date check adds 8. MRZ inconsistency adds 15. Tampering points are the measured tampering score multiplied by 20 and rounded. A verified face mismatch adds 15; unavailable face comparison adds zero. A missing trusted record adds only 5. Average OCR confidence below 0.50 adds 8; confidence from 0.50 to below 0.75 adds 5; higher confidence adds zero.

The bounded sum is capped at 100. Scores map to LOW RISK (0-24), MEDIUM RISK (25-49), REVIEW REQUIRED (50-74), and HIGH RISK (75-100). Reasons and per-factor points are returned alongside the score. A missing record contributes only the limited missing-reference factor; it is not by itself a fake-document determination. Threshold examples are covered by `tests/test_risk_score.py`.

## Decision limits

This is a screening aid, not an authenticity guarantee. Outputs can be wrong or incomplete. Secondary document review and authorized verification are required for consequential decisions.
