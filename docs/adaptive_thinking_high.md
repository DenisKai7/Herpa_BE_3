# Adaptive Thinking High

`thinking-high` now uses rule-based complexity assessment before external tools/refinement.

Simple intents:

- `compound-list`
- `herb-identity`
- `therapeutic-use-list`

Result: one model call, no PubMed/PubChem/protein target retrieval, no refinement.

Complex intents trigger extra tools/refinement only when keywords indicate mechanism, clinical evidence, HPLC/GC-MS, ADME, drug interactions, contraindications, dose, comparison, or research methodology.

Refinement metadata:

- simple: `execution_mode_used=thinking-high-single-pass`, `refinement_used=false`
- complex refined: `execution_mode_used=thinking-high-refined`, `refinement_used=true`
