from pydantic import BaseModel


class GroundedSource(BaseModel):
    source_type: str
    title: str
    identifier: str | None = None
    year: int | None = None
    url: str | None = None


class DataCoverage(BaseModel):
    herb_found: bool = False
    compounds_available: bool = False
    uses_available: bool = False
    sources_available: bool = False
    toxicity_available: bool = False
    clinical_data_available: bool = False
