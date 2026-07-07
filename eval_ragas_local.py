#!/usr/bin/env python3
"""HERPA — Standalone Local Ragas Evaluation Suite.

100% offline benchmark for the GraphRAG herbal medicine pipeline.
Requires only: local llama.cpp server + HuggingFace model cache.

Usage:
    python eval_ragas_local.py
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("herpa_ragas")

# ---------------------------------------------------------------------------
# 1. Dependency bootstrap — fail fast with actionable guidance
# ---------------------------------------------------------------------------

_MISSING: list[str] = []
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    _MISSING.append("langchain-openai")

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    _MISSING.append("langchain-huggingface")

try:
    from datasets import Dataset
except ImportError:
    _MISSING.append("datasets")

try:
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )
    from ragas.run_config import RunConfig
except ImportError:
    _MISSING.append("ragas")

if _MISSING:
    print(f"ERROR: Dependencies belum terinstall: {', '.join(_MISSING)}")
    print(f"  pip install {' '.join(_MISSING)}")
    sys.exit(1)

import pandas as pd

# ---------------------------------------------------------------------------
# 2. Local LLM — ChatOpenAI pointing to llama.cpp
# ---------------------------------------------------------------------------

LLAMA_BASE_URL = "http://localhost:8080/v1"
LLAMA_MODEL = "Qwen3-4B-Instruct-2507"
OUTPUT_CSV = "hasil_evaluasi_herpa_local.csv"

logger.info("Menghubungkan ke local llama.cpp → %s", LLAMA_BASE_URL)

local_llm = ChatOpenAI(
    base_url=LLAMA_BASE_URL,
    api_key="local-token",  # llama.cpp does not require real auth
    model=LLAMA_MODEL,
    temperature=0.1,
    max_tokens=512,
    request_timeout=900,  # generous timeout for local inference
)

# ---------------------------------------------------------------------------
# 3. Local Embeddings — HuggingFace on CPU/GPU, fully offline
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
logger.info("Memuat embedding model lokal → %s", EMBEDDING_MODEL)

local_embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# ---------------------------------------------------------------------------
# 4. High-Variance Herbal Ground-Truth Dataset
# ---------------------------------------------------------------------------

data_uji: list[dict] = [
    {
        "question": "Apa saja kandungan senyawa aktif pada jeruk nipis?",
        "contexts": [
            (
                "Jeruk nipis (Citrus aurantifolia) mengandung senyawa aktif utama: "
                "limonen, asam sitrat, flavonoid (hesperidin, naringin), vitamin C, "
                "dan minyak atsiri. Limonene merupakan komponen utama kulit buah "
                "yang bersifat antimikroba dan antioksidan."
            ),
            (
                "Penelitian fitokimia menunjukkan ekstrak jeruk nipis memiliki aktivitas "
                "antibakteri terhadap Staphylococcus aureus dan Escherichia coli. "
                "Kandungan flavonoid berkontribusi pada aktivitas antiinflamasi."
            ),
            (
                "Famili Rutaceae, genus Citrus. Nama ilmiah: Citrus aurantifolia. "
                "Tanaman ini kaya vitamin C (30-50 mg per 100g) dan mengandung "
                "asam askorbat, kalsium, serta kalium."
            ),
        ],
        "answer": (
            "Jeruk nipis (Citrus aurantifolia) mengandung senyawa aktif utama "
            "meliputi limonen, asam sitrat, flavonoid (hesperidin dan naringin), "
            "vitamin C, serta minyak atsiri. Limonene merupakan komponen utama "
            "pada kulit buah yang bersifat antimikroba dan antioksidan. "
            "Kandungan flavonoid berkontribusi pada aktivitas antiinflamasi."
        ),
        "ground_truth": (
            "Senyawa aktif jeruk nipis meliputi limonen, asam sitrat, "
            "flavonoid (hesperidin, naringin), vitamin C, dan minyak atsiri. "
            "Limonene bersifat antimikroba, flavonoid bersifat antiinflamasi, "
            "dan vitamin C berperan sebagai antioksidan kuat."
        ),
    },
    {
        "question": "Saya sering pusing di kepala bagian kiri, tanaman herbal apa yang bisa membantu?",
        "contexts": [
            (
                "Jahe (Zingiber officinale) mengandung gingerol dan shogaol yang "
                "memiliki aktivitas antiinflamasi dan analgesik. Studi klinis "
                "menunjukkan ekstrak jahe efektif mengurangi frekuensi migrain "
                "dibandingkan plasebo."
            ),
            (
                "Peppermint (Mentha piperita) mengandung mentol yang bersifat "
                "vasodilator topikal. Minyak esensial peppermint dioleskan pada "
                "pelipis terbukti meredakan tegangan kepala dalam 15 menit."
            ),
            (
                "Tanaman herbal untuk nyeri kepala: jahe (Zingiber officinale), "
                "peppermint (Mentha piperita), lavender (Lavandula angustifolia), "
                "dan feverfew (Tanacetum parthenium). Masing-masing mekanisme "
                "kerjanya berbeda: antiinflamasi, vasodilatasi, relaksasi, dan "
                "inhibisi agregasi trombosit."
            ),
        ],
        "answer": (
            "Untuk pusing di kepala bagian kiri, beberapa tanaman herbal yang "
            "dapat membantu antara lain: Jahe (Zingiber officinale) dengan kandungan "
            "gingerol dan shogaol yang bersifat antiinflamasi dan analgesik; "
            "Peppermint (Mentha piperita) yang mengandung mentol sebagai vasodilator "
            "topikal untuk meredakan tegangan kepala; serta lavender (Lavandula "
            "angustifolia) untuk relaksasi. Konsultasikan dengan tenaga medis jika "
            "gejala berlanjut."
        ),
        "ground_truth": (
            "Tanaman herbal untuk nyeri kepala bagian kiri meliputi jahe "
            "(Zingiber officinale) yang mengandung gingerol untuk antiinflamasi "
            "dan analgesik, peppermint (Mentha piperita) dengan mentol sebagai "
            "vasodilator topikal, serta lavender (Lavandula angustifolia) untuk "
            "efek relaksasi. Feverfew (Tanacetum parthenium) juga digunakan "
            "untuk pencegahan migrain."
        ),
    },
    {
        "question": "Apa mekanisme kerja senyawa allicin pada bawang putih?",
        "contexts": [
            (
                "Bawang putih (Allium sativum) mengandung alliin yang dikonversi "
                "menjadi allicin oleh enzim alliinase saat bawang dihancurkan. "
                "Allicin memiliki aktivitas antimikroba spektrum luas melalui "
                "inhibisi sintesis asam lemak (FAS II) pada bakteri."
            ),
            (
                "Senyawa organosulfur bawang putih: allicin, ajoene, dialil "
                "sulfida (DAS), dialil disulfida (DADS), S-allyl cysteine (SAC). "
                "Allicin bersifat unstable dan cepat metabolis menjadi ajoene "
                "dan DADS yang lebih stabil dalam tubuh."
            ),
            (
                "Studi in vitro menunjukkan allicin menghambat pertumbuhan "
                "Helicobacter pylori pada konsentrasi 5-25 mcg/mL. Mekanisme: "
                "modifikasi tiol intraseluler, depleksi glutation, dan induksi "
                "stres oksidatif pada sel patogen."
            ),
        ],
        "answer": (
            "Allicin pada bawang putih bekerja melalui beberapa mekanisme: "
            "pertama, inhibisi sintesis asam lemak (FAS II) pada bakteri sehingga "
            "memiliki aktivitas antimikroba spektrum luas. Kedua, modifikasi tiol "
            "intraseluler yang menyebabkan depleksi glutation dan induksi stres "
            "oksidatif pada sel patogen. Allicin dihasilkan dari konversi alliin "
            "oleh enzim alliinase saat bawang dihancurkan."
        ),
        "ground_truth": (
            "Mekanisme kerja allicin pada bawang putih meliputi: (1) inhibisi "
            "sintesis asam lemak FAS II pada bakteri bersifat antimikroba; "
            "(2) modifikasi tiol intraseluler menyebabkan depleksi glutation "
            "dan stres oksidatif pada patogen; (3) efektif terhadap H. pylori "
            "pada konsentrasi rendah. Allicin terbentuk dari alliin via enzim "
            "alliinase saat bawang dihancurkan."
        ),
    },
    {
        "question": "Jelaskan kegunaan terapeutik temulawak untuk kesehatan hati.",
        "contexts": [
            (
                "Temulawak (Curcuma xanthorrhiza) mengandung kurkuminoid "
                "(kurkumin, demetoksikurkumin) dan minyak atsiri (xanthorrhizol, "
                "germakron, ar-turmeron). Ekstrak temulawak terbukti "
                "hepatoprotektif pada model tikus yang diinduksi CCl4."
            ),
            (
                "Mekanisme hepatoproteksi temulawak: (1) antioksidan — menurunkan "
                "MDA dan meningkatkan SOD, katalase, GPx; (2) antiinflamasi — "
                "menghambat NF-kB dan COX-2; (3) kolagogum — merangsang sekresi "
                "empedu untuk membantu pencernaan lemak."
            ),
        ],
        "answer": (
            "Temulawak (Curcuma xanthorrhiza) memiliki kegunaan terapeutik "
            "untuk kesehatan hati melalui tiga mekanisme utama: aktivitas "
            "hepatoprotektif dengan menurunkan stres oksidatif (menurunkan MDA, "
            "meningkatkan SOD dan katalase), efek antiinflamasi melalui inhibisi "
            "NF-kB dan COX-2, serta sifat kolagogum yang merangsang sekresi "
            "empedu. Senyawa aktif utamanya adalah kurkuminoid dan xanthorrhizol."
        ),
        "ground_truth": (
            "Temulawak (Curcuma xanthorrhiza) bersifat hepatoprotektif melalui: "
            "(1) aktivitas antioksidan — menurunkan MDA, meningkatkan SOD, "
            "katalase, GPx; (2) antiinflamasi — menghambat jalur NF-kB dan COX-2; "
            "(3) kolagogum — merangsang sekresi empedu. Senyawa aktif: kurkumin, "
            "xanthorrhizol, germakron. Terbukti pada model tikus CCl4."
        ),
    },
    {
        "question": "Apa saja target protein dari senyawa ginsenosida pada ginseng?",
        "contexts": [
            (
                "Ginseng (Panax ginseng) mengandung ginsenosida Rb1, Rg1, Rg3, "
                "dan Rh2 sebagai senyawa aktif utama. Ginsenosida Rb1 berinteraksi "
                "dengan reseptor glukokortikoid dan modulasi jalur PI3K/Akt."
            ),
            (
                "Target protein ginsenosida: Ginsenosida Rg1 mengaktivasi reseptor "
                "estrogen (ER-alpha), Ginsenosida Rg3 menghambat VEGF/VEGFR2 "
                "pada angiogenesis tumor, Ginsenosida Rh2 menginduksi apoptosis "
                "melalui jalur mitokondria (Bax/Bcl-2, caspase-3)."
            ),
            (
                "Efek neuroprotektif ginsenosida Rb1 melalui aktivasi BDNF/TrkB "
                "dan jalur Nrf2/HO-1. Ginsenosida Rg1 meningkatkan neurogenesis "
                "di hippocampus melalui modulasi Wnt/beta-catenin."
            ),
        ],
        "answer": (
            "Ginsenosida pada ginseng (Panax ginseng) berinteraksi dengan "
            "beberapa target protein: Ginsenosida Rb1 — reseptor glukokortikoid, "
            "jalur PI3K/Akt, BDNF/TrkB, dan Nrf2/HO-1 untuk neuroproteksi; "
            "Ginsenosida Rg1 — reseptor estrogen ER-alpha dan Wnt/beta-catenin "
            "untuk neurogenesis; Ginsenosida Rg3 — VEGF/VEGFR2 untuk inhibisi "
            "angiogenesis tumor; Ginsenosida Rh2 — jalur Bax/Bcl-2 dan caspase-3 "
            "untuk induksi apoptosis."
        ),
        "ground_truth": (
            "Target protein ginsenosida: Rb1 → reseptor glukokortikoid, PI3K/Akt, "
            "BDNF/TrkB, Nrf2/HO-1; Rg1 → ER-alpha, Wnt/beta-catenin; "
            "Rg3 → VEGF/VEGFR2 (anti-angiogenesis); Rh2 → Bax/Bcl-2, caspase-3 "
            "(pro-apoptosis). Semua senyawa berasal dari Panax ginseng."
        ),
    },
]

logger.info("Dataset uji: %d test cases herbal", len(data_uji))

# ---------------------------------------------------------------------------
# 5. Build HuggingFace Dataset
# ---------------------------------------------------------------------------

ds = Dataset.from_dict({
    "question": [d["question"] for d in data_uji],
    "contexts": [d["contexts"] for d in data_uji],
    "answer": [d["answer"] for d in data_uji],
    "ground_truth": [d["ground_truth"] for d in data_uji],
})

# ---------------------------------------------------------------------------
# 6. Execute Ragas Evaluation
# ---------------------------------------------------------------------------

logger.info("Memulai evaluasi Ragas (metrics: faithfulness, answer_relevancy, context_precision, context_recall)...")
started = time.perf_counter()

# Configure run for local inference — low concurrency, high timeout
run_config = RunConfig(
    timeout=300,       # 5 min per LLM call
    max_retries=3,     # fewer retries to fail faster on real errors
    max_wait=120,      # max wait between retries
    max_workers=2,     # llama.cpp handles 1 request at a time
)

try:
    result = evaluate(
        dataset=ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=local_llm,
        embeddings=local_embeddings,
        run_config=run_config,
    )
    elapsed = round(time.perf_counter() - started, 2)
    logger.info("Evaluasi selesai dalam %.2f detik", elapsed)

    # ---------------------------------------------------------------------------
    # 7. Export Report
    # ---------------------------------------------------------------------------

    df = result.to_pandas()
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info("Report disimpan → %s", OUTPUT_CSV)

    # Print summary
    print()
    print("=" * 65)
    print("  HASIL EVALUASI RAGAS — HERPA GraphRAG (Local)")
    print("=" * 65)
    print(f"  Waktu eksekusi : {elapsed} detik")
    print(f"  Jumlah data uji: {len(data_uji)}")
    print(f"  LLM            : {LLAMA_MODEL} ({LLAMA_BASE_URL})")
    print(f"  Embeddings     : {EMBEDDING_MODEL}")
    print()
    print("  METRIK RATA-RATA:")
    print("  " + "-" * 50)

    # Compute averages from the dataframe
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for col in metric_cols:
        if col in df.columns:
            avg = df[col].mean()
            print(f"    {col:<25} : {avg:.4f}")
        else:
            print(f"    {col:<25} : N/A")

    print()
    print("  DETAIL PER TEST CASE:")
    print("  " + "-" * 50)
    for i, row in df.iterrows():
        q = str(row.get("question", ""))[:60]
        print(f"  [{i+1}] {q}")
        for col in metric_cols:
            if col in df.columns:
                val = row.get(col)
                if val is not None and not pd.isna(val):
                    print(f"      {col:<23}: {val:.4f}")
        print()

    print(f"  CSV Report: {OUTPUT_CSV}")
    print("=" * 65)

except ConnectionError as exc:
    elapsed = round(time.perf_counter() - started, 2)
    logger.error("Gagal menghubungi llama.cpp server setelah %.2f detik", elapsed)
    logger.error("Pastikan llama-server.exe berjalan di %s", LLAMA_BASE_URL)
    logger.error("Detail: %s", exc)
    sys.exit(1)

except Exception as exc:
    elapsed = round(time.perf_counter() - started, 2)
    logger.error("Evaluasi gagal setelah %.2f detik: %s", elapsed, exc)
    logger.warning(
        "Kemungkinan penyebab: (1) llama.cpp server mati, "
        "(2) model embedding belum di-cache, (3) timeout. "
        "Periksa log di atas untuk detail."
    )
    sys.exit(1)
