# Herbal Detail Factual Rendering

## Prinsip
Detail drawer/tab menampilkan data faktual dari endpoint `/api/herbal-recommendations/herbs/{herb_id}/detail`. Jika data tidak ada, tampilkan fallback yang jujur — bukan `(missing)`, bukan `belum lolos verifikasi`.

## Rendering per Section

### 1. Bagian Tanaman (`plant_parts`)
```
Jika ada: rimpang, daun, buah, dll.
Jika kosong: "Bagian tanaman belum tersedia pada knowledge graph."
```
**DILARANG**: "Informasi ini tidak ditampilkan karena belum lolos verifikasi."

### 2. Ketersediaan/Penyimpanan (`storage_guidelines`)
```
Jika ada: tampilkan title, description, storage_temperature
Jika kosong: "Ketersediaan belum tercatat secara spesifik pada knowledge graph."
```
**DILARANG**: "Ketersediaan belum dapat dipastikan."

### 3. Cara Pengolahan (`preparation_methods`)
```
Jika ada: title, method_type, plant_part, ingredients, steps, notes
Jika kosong: "Cara pengolahan belum tercatat pada knowledge graph untuk kandidat ini."
```

### 4. Aturan Pakai (`usage_guidelines`)
```
Jika ada: title, description, frequency_text, duration_text, dose_status
Jika kosong: "Aturan pakai spesifik belum tercatat pada knowledge graph. Gunakan informasi herbal secara hati-hati dan konsultasikan dengan tenaga kesehatan bila gejala menetap."
```

### 5. Peringatan (`safety_warnings`, `contraindications`, `drug_interactions`)
```
Jika ada: tampilkan per section
Jika kosong: "Belum ada peringatan spesifik yang tercatat pada knowledge graph. Tetap berhati-hati bila sedang hamil, menyusui, memiliki penyakit kronis, atau menggunakan obat rutin."
```

### 6. Kontraindikasi
```
Jika ada: condition, description, severity
Jika kosong: "Belum ada kontraindikasi spesifik yang tercatat pada knowledge graph."
```
**DILARANG**: "Kontraindikasi (missing)"

### 7. Interaksi Obat
```
Jika ada: substance, description, severity
Jika kosong: "Belum ada interaksi spesifik yang tercatat pada knowledge graph."
```
**DILARANG**: "Interaksi (missing)"

### 8. Kelompok Berisiko
```
Jika ada: population_risks dari safety_warnings dan contraindications
Jika kosong: "Belum ada kelompok berisiko spesifik yang tercatat pada knowledge graph."
```
**DILARANG**: "Kelompok berisiko (missing)"

### 9. Efek Samping
```
Jika ada: dari safety_warnings dengan severity
Jika kosong: "Belum ada efek samping spesifik yang tercatat pada knowledge graph."
```
**DILARANG**: "Efek samping (missing)"

## Frontend Helper Functions

```typescript
getPlantPartDisplay(item)        // → string
getAvailabilityDisplay(item)     // → string
getPreparationDisplay(item)      // → string
getUsageGuidelineDisplay(item)   // → string
getSafetyDisplay(item)           // → { warnings, contraindications, interactions, populationRisks, hasSafetyData, fallbackMessage }
```
