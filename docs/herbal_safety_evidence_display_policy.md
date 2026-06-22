# Herbal Safety & Evidence Display Policy

## Safety Status Resolving

### Aturan
Safety label ditentukan berdasarkan data faktual, bukan default "Perlu perhatian".

```python
resolve_safety_status(
    toxicity, contraindications, interactions, user_context, initial_status
) → (status, label, notes)
```

### Hierarki

| Kondisi | Status | Label |
|---------|--------|-------|
| Toksik berat (fatal, dilarang) | unsafe | Tidak disarankan |
| Kontraindikasi kehamilan + user hamil | unsafe | Tidak aman |
| Ada kontraindikasi/interaksi | caution | Perlu perhatian |
| Ada warning/toxicity (tanpa kontraindikasi) | limited | Data keamanan terbatas |
| initial_status dari graph = safe/limited/caution | (sesuai) | (sesuai) |
| Tidak ada data | unknown | Data keamanan belum cukup |

### Hal yang DILARANG
- Semua herb mendapat label "Perlu perhatian"
- Menggunakan kata "missing" di label safety
- Menampilkan "Perlu perhatian" tanpa ada kontraindikasi/interaksi spesifik

## Evidence Status Resolving

```python
resolve_evidence_status(sources, traditional_uses, claims) → (status, label)
```

| Kondisi | Status | Label |
|---------|--------|-------|
| Ada source objects | available | Data sumber tersedia |
| Ada claims | limited | Data klaim tersedia |
| Ada traditional uses | traditional | Data tradisional tersedia |
| Tidak ada data | unavailable | Data bukti belum tersedia |

### Hal yang DILARANG
- Menampilkan "Data bukti belum tersedia" jika ada data tradisional
- Label evidence kontradiksi dengan data yang ada

## Data Status (Card)

```python
resolve_data_status(candidate) → (status, label)
```

| Kondisi | Status | Label |
|---------|--------|-------|
| Ada sources | source_available | Data sumber tersedia |
| Ada traditional + compounds | kg_supported | Didukung data knowledge graph |
| Ada traditional | traditional_available | Data tradisional tersedia |
| Ada compounds | compound_available | Data senyawa tersedia |
| Ada detail data | detail_available | Data detail tersedia |
| Tidak ada | limited | Data masih terbatas |

### Hal yang DILARANG
- Default "Data belum dapat dipastikan"

## Safety Display di Detail

Jika data ada → tampilkan per section (warnings, contraindications, interactions, population_risks)

Jika kosong:
```
"Belum ada peringatan spesifik yang tercatat pada knowledge graph. 
Tetap berhati-hati bila sedang hamil, menyusui, memiliki penyakit kronis, 
atau menggunakan obat rutin."
```

### Teks yang DILARANG di UI
- `(missing)`
- `Kontraindikasi (missing)`
- `Interaksi (missing)`
- `Kelompok berisiko (missing)`
- `Efek samping (missing)`
