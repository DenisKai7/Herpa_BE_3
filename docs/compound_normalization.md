# Compound Normalization

`app/graph/compound_normalizer.py` normalizes compound rows before formatting.

Rules:

1. Prefer valid PubChem CID for dedupe.
2. Else dedupe by normalized name.
3. Strip concentration/percentage markers.
4. Normalize Unicode dashes.
5. Treat IUPAC as metadata, not a separate public display compound.
6. Hide IUPAC for persona `umum`.
7. Classify nutrients separately from active phytochemicals.

Component kinds:

- `phytochemical`
- `amino_acid`
- `vitamin`
- `mineral`
- `macronutrient`
- `unknown`
