from app.services.documents.image_processor import ImageProcessor


def test_parse_structured_json():
    raw_json = """
    {
      "plant_candidates": [
        {
          "local_name": "Daun Sirih",
          "scientific_name": "Piper betle",
          "confidence": 0.9,
          "visual_cues": ["daun berbentuk hati", "tulang daun jelas"]
        }
      ],
      "visual_summary": "Daun hijau berbentuk hati",
      "not_likely": [
        {
          "name_local": "Daun Alpukat",
          "scientific_name": "Persea americana",
          "reason": "Morfologi berbeda"
        }
      ],
      "limitations": []
    }
    """
    parsed = ImageProcessor._parse_structured(raw_json)
    assert parsed["plant_candidates"][0]["local_name"] == "Daun Sirih"
    assert parsed["plant_candidates"][0]["scientific_name"] == "Piper betle"
    assert parsed["plant_candidates"][0]["confidence"] == 0.9
    assert parsed["visual_summary"] == "Daun hijau berbentuk hati"
    assert parsed["not_likely"][0]["name_local"] == "Daun Alpukat"
    assert parsed["text"] == "Daun hijau berbentuk hati"


def test_parse_structured_with_markdown():
    raw_md = """
    ```json
    {
      "plant_candidates": [
        {
          "local_name": "Kunyit",
          "scientific_name": "Curcuma longa",
          "confidence": 0.85
        }
      ],
      "visual_summary": "Rimpang berwarna oranye",
      "not_likely": [
        {
          "name_local": "Temulawak",
          "scientific_name": "Curcuma xanthorrhiza",
          "reason": "Morfologi rimpang berbeda"
        }
      ]
    }
    ```
    """
    parsed = ImageProcessor._parse_structured(raw_md)
    assert parsed["plant_candidates"][0]["local_name"] == "Kunyit"
    assert parsed["plant_candidates"][0]["scientific_name"] == "Curcuma longa"
    assert parsed["plant_candidates"][0]["confidence"] == 0.85
    assert parsed["visual_summary"] == "Rimpang berwarna oranye"
    assert parsed["not_likely"][0]["name_local"] == "Temulawak"


def test_parse_structured_fallback():
    raw_text = "Ini adalah gambar daun hijau dengan tepi bergerigi kasar."
    parsed = ImageProcessor._parse_structured(raw_text)
    assert parsed["plant_candidates"] == []
    assert parsed["visual_summary"] == raw_text
    assert parsed["text"] == raw_text
    assert "model vlm tidak menghasilkan format terstruktur" in parsed["limitations"][0].lower()
