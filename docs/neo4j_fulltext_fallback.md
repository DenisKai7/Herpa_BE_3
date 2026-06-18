# Neo4j Full-Text Index & Property Fallback

## Alur Resolusi Pencarian Tanaman
Saat index pencarian full-text `herb_fulltext_idx` belum teralokasikan atau offline di Aura DB, backend secara otomatis mendegradasi alur ke property-search fallback untuk menghindari kegagalan sistem.

```text
Query "kunyit"
  │
  ├── 1. Coba full-text: HERB_FULLTEXT_SEARCH (db.index.fulltext.queryNodes)
  │
  ├── 2. Jika sukses ──> Return data tanaman
  │
  └── 3. Jika gagal (AppError index missing)
        │
        ├── Log warning "herb_fulltext_index_unavailable_using_fallback"
        │
        └── Coba property fallback: HERB_PROPERTY_SEARCH_FALLBACK
              │
              └── Return data tanaman (status: property-fallback)
```

## Idempotent Index Creation
Index full-text dideklarasikan di `database/neo4j/performance_indexes.cypher` dan harus dijalankan secara manual pada Aura database console.

```cypher
CREATE FULLTEXT INDEX herb_fulltext_idx IF NOT EXISTS
FOR (h:Herb)
ON EACH [
    h.commonName,
    h.canonicalScientificName,
    h.latinName,
    h.localNames
];
```
