# HERBAL RECOMMENDATION SAFETY & SCORING FIX REPORT

## Cause of Issues
- Cypher referenced `h.safety_status` directly, generating `UnknownPropertyKeyWarning` warnings.
- Backend calculated confidence scores strictly with local lists instead of leveraging Neo4j calculated values.

## Fixes Implemented
- **Idempotent Cypher scripts:** Created scripts to update safety status properties and indexes on DB safely.
- **Improved Cypher scoring:** Configured safety status derivation using relationship exists checks, avoiding raw property warnings.
- **Granular Scoring v2:** Computed compound scaling and safety score maps dynamically.
- **Candidate Warnings Propagation:** Appended warnings on caution safety status at both candidate and response levels.
- **Frontend TS Helper:** Added `getCandidateQualityLabel` and `getSafetyStatusLabel` functions.

## Validation Results
Pending tests.
