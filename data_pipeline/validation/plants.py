from pydantic import BaseModel, Field


class CompoundSeed(BaseModel):
    compound_id: str
    name: str
    pubchem_cid: str | None = None


class PlantSeed(BaseModel):
    plant_id: str
    local_name: str
    scientific_name: str
    family: str | None = None
    parts: list[str] = Field(default_factory=list)
    compounds: list[CompoundSeed] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    evidence_level: str = "unknown"
