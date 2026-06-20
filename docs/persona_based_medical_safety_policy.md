# Persona-Based Medical Safety Policy

Global disclaimer: `Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan.`

Forbidden output:
- claim menyembuhkan
- diagnosis penyakit
- instruksi menghentikan obat dokter
- instruksi mengganti terapi medis dengan herbal
- dosis klinis angka untuk persona `umum` tanpa sumber/konteks

Persona visibility:
- `umum`: traditional uses, preparation, usage guideline edukatif, warnings, plant parts, storage, myth/fact, brief sources. Clinical dose hidden.
- `pelajar`: umum + education/phytochemistry concepts where available.
- `peneliti`: claims, evidence, research topics, quality standards, pharmacokinetics.
- `tenaga_medis`: clinical guidelines, drug interactions, contraindications, pharmacokinetics, population risks.

If clinical dose exists for `umum`, show safe notice instead of detail.
