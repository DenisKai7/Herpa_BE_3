# Direct Answer Engine

Fast-medium direct path handles `compound-list`, `herb-identity`, and `therapeutic-use-list` without llama.cpp when Neo4j data is enough.

Flow:

1. Normalize + classify query via `app/services/ai/query_intent.py`.
2. Resolve herb with existing graph resolver/repository.
3. Fetch minimal context only: herb, compounds, sources.
4. Normalize/deduplicate compounds.
5. Format persona-specific deterministic answer.
6. Persist metadata with `direct_answer_used=true`, `model_calls=0`, `finish_reason=complete`.

No PubMed, PubChem, protein targets, full history, or refinement for simple direct intents.
