# Direct Answer Architecture

Fast-medium direct answers use deterministic execution:

`intent -> herb resolution -> minimal Neo4j context -> compound normalization -> persona formatter -> metadata -> persist/stream`

Handled intents:

- `compound-list`
- `herb-identity`
- `therapeutic-use-list`

Skipped for direct path:

- llama.cpp
- PubMed
- PubChem
- protein targets
- refinement
- full history

Metadata includes `direct_answer_used=true`, `model_calls=0`, `refinement_used=false`.
