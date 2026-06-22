# Herbal Card Label Policy

## Prinsip
Card rekomendasi herbal menampilkan label berdasarkan **data faktual** dari response backend, bukan hardcoded.

## Label yang Ditampilkan

### 1. Relevansi
```
Label: item.relevance_label (dari backend)
Persen: item.relevance_percent (dari backend)
```
**Aturan**: Label dan persen HARUS berasal dari field yang sama (`confidence`/`relevance_score`).

| Score | Level | Label | Persen |
|-------|-------|-------|--------|
| ≥ 0.75 | high | Relevansi tinggi | 75-100% |
| ≥ 0.50 | medium | Relevansi sedang | 50-74% |
| ≥ 0.25 | low | Relevansi rendah | 25-49% |
| > 0 | initial | Kandidat awal | 1-24% |
| 0 | unknown | Relevansi belum tersedia | 0% |

**DILARANG**: `Relevansi tinggi (0%)` — label dan persen harus sinkron.

### 2. Kecocokan Gejala (terpisah dari relevansi)
```
item.symptom_coverage_percent
```
Ditampilkan sebagai badge terpisah jika diinginkan.

### 3. Data Status
```
Label: item.data_status_label (dari backend)
```

| Status | Label |
|--------|-------|
| source_available | Data sumber tersedia |
| kg_supported | Didukung data knowledge graph |
| traditional_available | Data tradisional tersedia |
| compound_available | Data senyawa tersedia |
| detail_available | Data detail tersedia |
| limited | Data masih terbatas |

**DILARANG**: `Data belum dapat dipastikan` sebagai default.

### 4. Safety Status
```
Label: item.safety_label (dari backend)
```

| Status | Label | Kapan |
|--------|-------|-------|
| safe | Relatif aman | h.safety_status = 'safe' |
| limited | Data keamanan terbatas / Perlu kehati-hatian | warning/toxicity tanpa kontraindikasi |
| caution | Perlu perhatian | Ada kontraindikasi/interaksi |
| unsafe | Tidak disarankan | Toksik berat |
| unknown | Data keamanan belum cukup | Tidak ada data |

**DILARANG**: Semua herb menjadi `Perlu perhatian`.

### 5. Evidence Status
```
Label: item.evidence_label (dari backend)
```

| Status | Label |
|--------|-------|
| available | Data sumber tersedia |
| clinical | Bukti klinis tersedia |
| limited | Data klaim tersedia |
| traditional | Data tradisional tersedia |
| unavailable | Data bukti belum tersedia |

## Frontend Helper Functions

```typescript
getRelevanceLabelForCard(item)    // → string label
getRelevancePercent(item)         // → number 0-100
getSafetyLabelForCard(item)       // → string label
getEvidenceLabelForCard(item)     // → string label
getCandidateQualityLabel(item)    // → string data status label
getSymptomCoveragePercent(item)   // → number 0-100
```
