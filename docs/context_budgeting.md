# Context Budgeting & Estimator

## Context Budget Formula
Alokasi budget untuk prompt input dihitung dengan:
$$\text{input\_budget} = \text{context\_size} - \text{output\_tokens} - \text{safety\_margin}$$

## Conservative Token Estimator
Sistem menggunakan estimator konservatif untuk memperkirakan ukuran token jika tokenizer remote tidak tersedia:
$$\text{estimated\_tokens} = \max(1, \text{len(text)} / 3)$$

## Alur Pemangkasan Konteks (Trimming Priority)
Jika jumlah token melebihi budget, pemangkasan dilakukan dengan prioritas berikut:
1. **Safety Prompt & User Query**: Tidak boleh dipotong.
2. **Old History**: Pesan riwayat tertua dihapus terlebih dahulu.
3. **Deskripsi Mikroskopis**: Dihapus jika context size terbatas.
4. **Protein Targets**: Dihapus jika user tidak menanyakan mekanisme molekuler secara spesifik.
5. **IUPAC Names**: Dihapus dari fitting facts khusus untuk persona **Umum**.
