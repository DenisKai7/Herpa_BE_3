# Neo4j Query Performance HERPA

## Masalah Awal (Cartesian Explosion)
Query awal menggabungkan banyak `OPTIONAL MATCH` (compounds, therapeutic_uses, protein_targets, toxicity, sources, families) secara linear.  
Jika satu Herb memiliki:
- 30 compounds
- 12 therapeutic uses
- 5 protein targets
- 2 toxicity categories
- 5 sources
- 1 family
  
Maka baris hasil query dikalikan secara Cartesian:  
$30 \times 12 \times 5 \times 2 \times 5 \times 1 = 18,000$ baris!  
Hal ini memicu overload memori, timeout, connection resets (`WinError 10054`), dan pemborosan bandwidth Aura DB.

## Solusi (Split Queries + Parallel Fetch)
Query dipecah menjadi 7 query independen yang ringan dan beroperasi dengan filter terarah `id`:
1. `FIND_HERBS_FALLBACK` / `FIND_HERBS_FULLTEXT` (mencari Herb utama, mengembalikan id & properties dasar).
2. `HERB_COMPOUNDS` (mengambil senyawa Herb, limit 12/25).
3. `HERB_THERAPEUTIC_USES` (mengambil therapeutic uses, limit 8/15).
4. `HERB_FAMILY` (mengambil famili, limit 5).
5. `HERB_PROTEIN_TARGETS` (mengambil target protein, limit 0/10).
6. `HERB_TOXICITY` (mengambil kategori toksisitas, limit 10).
7. `HERB_SOURCES` (mengambil sumber verifikasi, limit 3/8).

## Hasil Hydration Paralel
Di dalam `app/graph/repositories.py`, metode `_hydrate_herb` memanggil ketujuh query ini secara paralel menggunakan `asyncio.gather`:

```python
families, compounds, therapeutic_uses, targets, toxicity, sources = await asyncio.gather(
    self.get_herb_family(herb_id, limit=5, cache_ttl=cache_ttl),
    self.get_herb_compounds(herb_id, limit=30, cache_ttl=cache_ttl),
    self.get_herb_therapeutic_uses(herb_id, limit=30, cache_ttl=cache_ttl),
    self.get_herb_protein_targets(herb_id, limit=20, cache_ttl=cache_ttl),
    self.get_herb_toxicity(herb_id, limit=10, cache_ttl=cache_ttl),
    self.get_herb_sources(herb_id, limit=10, cache_ttl=cache_ttl),
)
```

Jumlah data yang ditarik maksimal hanya:  
$1 + 5 + 30 + 30 + 20 + 10 + 10 = 106$ baris!  
Latensi terpangkas drastis dan connection reset teratasi sepenuhnya.
