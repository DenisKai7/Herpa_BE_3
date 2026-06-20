# Frontend Recommendation Detail Tabs

Full frontend app not present in this backend repo. Apply this contract in Herpa_FE detail component.

Tabs:
1. Ringkasan: name, scientific name, relevance/score, reason, related symptoms, compounds, plant parts.
2. Penggunaan Tradisional: `item.traditional_uses ?? item.enrichment?.traditional_uses`; fallback: `Informasi penggunaan tradisional belum tersedia pada knowledge graph.`
3. Cara Pengolahan: `item.preparation_methods ?? item.enrichment?.preparation_methods`; show title, method_type, plant_part, ingredients, steps, notes, formulations; fallback clear.
4. Aturan Pakai: `item.usage_guidelines ?? item.enrichment?.usage_guidelines`; show frequency/duration/dose_status; fallback caution text.
5. Peringatan: combine `safety_warnings`, `drug_interactions_detail`, `contraindications_detail`, `safety_notes`, response red flags.
6. Sumber: aggregate `evidence_sources`, nested sources, `claims.sources`; dedupe via `dedupeSources`; do not show “Sumber Terpercaya” when empty.
7. Lanjutan: persona-based advanced sections.

Helpers provided: `frontend_patch/src/lib/recommendationEnrichment.ts`.
