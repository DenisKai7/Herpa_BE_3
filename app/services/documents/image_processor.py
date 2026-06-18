from app.services.ai.model_gateway import ModelGateway


class ImageProcessor:
    def __init__(self, gateway: ModelGateway):
        self.gateway = gateway

    async def analyze(self, data: bytes, mime_type: str, user_query: str) -> dict:
        prompt = (
            "Analisis gambar berikut untuk konteks tanaman herbal, produk herbal, struktur kimia, tabel, atau grafik. "
            "Jangan menyimpulkan identitas tanaman secara pasti bila ciri visual tidak cukup. Jelaskan observasi, kemungkinan, keterbatasan, dan relevansinya dengan pertanyaan: "
            + user_query
        )
        text = await self.gateway.analyze_image(data, mime_type, prompt)
        return {"text": text, "needs_vision": False, "source_type": "attachment_visual"}
