import json
from app.services.ai.model_gateway import ModelGateway

PLANT_ID_PROMPT = """Anda adalah asisten visual botani. Identifikasi tanaman pada gambar berdasarkan ciri visual saja.
Fokus pada: bentuk daun, tipe daun (daun tunggal atau daun majemuk), susunan anak daun pada tangkai, ukuran relatif anak daun, warna, tulang daun, tepi daun, dan bentuk tangkai.
Jangan memilih tanaman dari database jika ciri visual morfologinya tidak cocok.
Bila gambar menunjukkan daun majemuk menyirip ganda dengan banyak anak daun kecil berbentuk oval/bulat telur yang tersusun berpasangan pada satu tangkai, pertimbangkan kelor (Moringa oleifera) sebagai kandidat utama, dan JANGAN menebak alpukat (Persea americana) karena alpukat adalah daun tunggal besar berbentuk oval-lanset.

Kembalikan HANYA JSON valid (tanpa markdown) dengan format:
{
  "visual_summary": "deskripsi singkat ciri visual morfologi utama daun/tanaman pada gambar",
  "morphology": {
    "leaf_type": "simple|compound|unknown",
    "arrangement": "susunan daun/anak daun (misal: menyirip ganda)",
    "leaflet_count": "banyak/sedikit/angka perkiraan",
    "leaflet_shape": "bentuk anak daun (misal: oval)",
    "confidence": 0.0-1.0
  },
  "plant_candidates": [
    {
      "local_name": "nama umum Indonesia (misal: Daun kelor)",
      "scientific_name": "nama ilmiah (misal: Moringa oleifera)",
      "confidence": 0.0-1.0,
      "visual_evidence": ["ciri visual 1", "ciri visual 2"],
      "uncertainty": "ketidakpastian"
    }
  ],
  "not_likely": [
    {
      "local_name": "nama umum Indonesia (misal: Daun alpukat)",
      "scientific_name": "nama ilmiah (misal: Persea americana)",
      "reason": "alasan morfologi visual mengapa tanaman ini tidak cocok/kemungkinan kecil"
    }
  ],
  "limitations": ["keterbatasan analisis visual dari gambar ini"],
  "clarification_questions": ["pertanyaan klarifikasi jika visual kurang jelas"]
}
Jangan mengarang. Jika ciri visual tidak cukup, confidence rendah dan isi limitations.
Maksimal 3 kandidat, urutkan dari confidence tertinggi."""


class ImageProcessor:
    def __init__(self, gateway: ModelGateway):
        self.gateway = gateway

    async def analyze(self, data: bytes, mime_type: str, user_query: str) -> dict:
        prompt = PLANT_ID_PROMPT
        if user_query and user_query not in ("Analisis attachment ini", ""):
            prompt += f"\n\nPertanyaan pengguna: {user_query}"
        text = await self.gateway.analyze_image(data, mime_type, prompt)
        parsed = self._parse_structured(text)
        parsed["source_type"] = "attachment_visual"
        parsed["needs_vision"] = False
        return parsed

    @staticmethod
    def _parse_structured(raw: str) -> dict:
        """Parse VLM JSON output with graceful fallback to free text."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # Strip markdown code blocks
                if cleaned.startswith("```json"):
                    cleaned = cleaned.split("```json", 1)[-1]
                else:
                    cleaned = cleaned.split("```", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            if isinstance(data, dict):
                candidates = data.setdefault("plant_candidates", [])
                if isinstance(candidates, list):
                    for cand in candidates:
                        if isinstance(cand, dict):
                            cues = cand.get("visual_cues") or cand.get("visual_evidence") or []
                            cand["visual_cues"] = cues
                            cand["visual_evidence"] = cues
                not_likely = data.setdefault("not_likely", [])
                if isinstance(not_likely, list):
                    for item in not_likely:
                        if isinstance(item, dict):
                            name = item.get("local_name") or item.get("name_local") or ""
                            item["local_name"] = name
                            item["name_local"] = name
                data.setdefault("morphology", {
                    "leaf_type": "unknown",
                    "arrangement": "unknown",
                    "leaflet_count": "unknown",
                    "leaflet_shape": "unknown",
                    "confidence": 0.0
                })
                data["text"] = data.get("visual_summary", "")
                data["vlm_failed"] = False
                return data
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        # Fallback: treat entire response as visual_summary
        return {
            "plant_candidates": [],
            "visual_summary": raw[:2000],
            "morphology": {
                "leaf_type": "unknown",
                "arrangement": "unknown",
                "leaflet_count": "unknown",
                "leaflet_shape": "unknown",
                "confidence": 0.0
            },
            "not_likely": [],
            "limitations": ["Model VLM tidak menghasilkan format terstruktur."],
            "text": raw[:2000],
            "vlm_failed": True,
        }
