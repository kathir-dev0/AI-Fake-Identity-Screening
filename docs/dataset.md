# Dataset and Demo Registry

## Source and privacy

The MVP uses no real-person dataset. `data/trusted_registry.db` is a local mock reference registry with synthetic examples such as `CERT001 / ARUN KUMAR / 21CS001 / 9.0` and `P0001 / RAHUL SHARMA`. Those identifiers and names are fictional examples and do not represent government or institutional records.

One synthetic educational-certificate image is bundled at `sample_data/genuine/veridoc_demo_certificate.png`. It is a fictional UI/test fixture and the only image eligible for Demo OCR Fallback. The fallback compares image pixels to the bundled asset; edited, re-compressed, scanned, or unknown images do not receive predefined OCR fields. No face photos are bundled, and `reference_face` fields are empty by default, so face comparison normally returns `NOT_AVAILABLE`.

## Test scenarios

Use only hand-created synthetic files under `sample_data/genuine/` and `sample_data/tampered/`:

- Synthetic genuine certificate matching `CERT001`.
- Copy with a modified certificate number, name, institution, or register number.
- Photo-swapped synthetic copy when a synthetic face reference is configured.
- Synthetic record with an expired, revoked, or blacklisted status.
- Unknown identifier with no registry record.

Do not create or store real Aadhaar/passport documents, college records, or other personal identity data. The `.gitignore` excludes contents of genuine/tampered sample folders by default.
