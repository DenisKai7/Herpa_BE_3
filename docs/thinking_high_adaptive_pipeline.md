# Thinking High Adaptive Pipeline

Thinking-high uses one draft call for simple intents and optional bounded correction for complex intents.

Simple intents:

- `compound-list`
- `herb-identity`
- `therapeutic-use-list`

Behavior:

- external tools skipped unless complexity says needed
- refinement disabled
- metadata: `execution_mode_used=thinking-high-single-pass`, `model_calls=1`, `refinement_used=false`

Complex intents:

- mechanisms
- clinical evidence
- HPLC/GC-MS/LC-MS
- ADME/pharmacokinetics
- safety/interactions/contraindications
- comparisons

Behavior:

- max two model calls
- one short continuation only on `finish_reason=length`
- refinement/correction bounded by refinement token budget
