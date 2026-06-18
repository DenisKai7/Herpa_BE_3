# Final Latency + Persona Audit

## 1. Why Fast Medium called LLM
Previous flow always entered `AgenticGraph._run_fast_medium`, executed broad retrieval, then `gateway.generate_text/stream_text`. Direct deterministic path now intercepts simple intents before LLM.

## 2. Why Thinking High called model twice
Previous complexity rules enabled refinement for broad conditions/persona. Now simple intents force `requires_refinement=false`; complex refinement remains capped.

## 3. Prompt size
Context is bounded by `fit_messages_to_context`; benchmark records estimated input tokens. Direct fast-medium uses no LLM prompt.

## 4. History sent
Fast-medium direct sends zero history to LLM. Fallback budget keeps history low through context trimming.

## 5. GraphRAG data sent
Compound-list direct path fetches herb identity, compounds, sources only. It does not fetch targets/toxicity/full uses.

## 6. Model call count per mode
Fast-medium direct: 0. Fast-medium fallback: guarded to 1 + continuation only if truncated. Thinking-high simple: 1. Thinking-high complex: max 2.

## 7. Why IUPAC appeared
IUPAC-like strings were treated as compound names. Normalizer now treats IUPAC as metadata and hides it for `umum`.

## 8. Why generic sources appeared
Prompts could invent source names. Direct formatter now only uses `VERIFIED_BY`/actual source objects.

## 9. Why answers were truncated
`finish_reason` was not tracked. It is now captured; `length` triggers one short continuation.

## 10. Largest latency point
llama.cpp generation dominates. Partial benchmark showed thinking-high rows 121–175s while direct fast-medium was 8–1606ms.
