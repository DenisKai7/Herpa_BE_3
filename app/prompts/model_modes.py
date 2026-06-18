from app.core.constants import ModelMode, Persona
from app.prompts.base_system import BASE_SYSTEM_PROMPT
from app.prompts.persona_response_policy import persona_policy
from app.prompts.personas import persona_prompt

FAST_MEDIUM_PROMPT = """
Jawab langsung, relevan, dan efisien.
Gunakan fakta terverifikasi yang tersedia.
Ikuti gaya persona.
Jangan menampilkan proses berpikir internal.
Jika data tidak cukup, nyatakan keterbatasannya.
""".strip()

THINKING_HIGH_PROMPT = """
Susun jawaban komprehensif berdasarkan fakta dan sumber yang relevan.
Periksa hubungan antara klaim, bukti, kontraindikasi, serta keterbatasan.
Ikuti gaya persona.
Jangan menampilkan chain-of-thought atau proses internal.
Tampilkan hanya kesimpulan, penjelasan, sumber, dan keterbatasan yang aman.
""".strip()

REFINEMENT_PROMPT = """
Periksa draft terhadap fakta terverifikasi.
Hapus klaim yang tidak didukung.
Perbaiki struktur dan kejelasan.
Tambahkan keterbatasan jika diperlukan.
Jangan menambahkan fakta baru tanpa sumber.
Jangan menampilkan proses pemeriksaan internal.
""".strip()


def build_system_prompt(persona: Persona, model_mode: ModelMode) -> str:
    mode_prompt = THINKING_HIGH_PROMPT if model_mode == ModelMode.THINKING_HIGH else FAST_MEDIUM_PROMPT
    return "\n\n".join(
        [BASE_SYSTEM_PROMPT, persona_prompt(persona.value), persona_policy(persona, model_mode), mode_prompt]
    )


def refinement_prompt() -> str:
    return REFINEMENT_PROMPT
