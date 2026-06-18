from typing import Any
from urllib.parse import quote
from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.external.http_client import ExternalHttpClient


class PubChemTool:
    BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, settings: Settings, http: ExternalHttpClient):
        self.settings = settings
        self.http = http

    async def compound(self, name: str) -> dict[str, Any] | None:
        if not self.settings.enable_pubchem:
            return None
        props = "MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,InChI,InChIKey,IUPACName"
        try:
            response = await self.http.get(
                f"{self.BASE}/compound/name/{quote(name, safe='')}/property/{props}/JSON"
            )
            values = response.json().get("PropertyTable", {}).get("Properties", [])
        except Exception as exc:
            raise AppError("EXTERNAL_TOOL_UNAVAILABLE", "PubChem tidak dapat diakses.", 503) from exc
        if not values:
            return None
        item = values[0]
        cid = item.get("CID")
        return {
            "source_id": f"pubchem:{cid}",
            "cid": cid,
            "name": name,
            "molecular_formula": item.get("MolecularFormula"),
            "molecular_weight": item.get("MolecularWeight"),
            "canonical_smiles": item.get("ConnectivitySMILES") or item.get("CanonicalSMILES"),
            "isomeric_smiles": item.get("SMILES") or item.get("IsomericSMILES"),
            "inchi": item.get("InChI"),
            "inchikey": item.get("InChIKey"),
            "iupac_name": item.get("IUPACName"),
            "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        }
