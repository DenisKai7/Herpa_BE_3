import { isAxiosError } from "axios";
import type { HerbalRecommendationItem, Persona, SourceReference } from "../types/backend";

export function getVerificationLabel(status?: string) {
  switch (status) {
    case "verified":
      return "Terverifikasi";
    case "limited":
      return "Data terbatas";
    case "traditional":
      return "Penggunaan tradisional";
    case "unavailable":
      return "Belum tersedia";
    default:
      return "Status belum diketahui";
  }
}

export function getEvidenceLabel(level?: string) {
  switch (level) {
    case "available":
      return "Data sumber tersedia";
    case "traditional":
      return "Data tradisional tersedia";
    case "limited":
      return "Data terbatas";
    case "clinical":
      return "Bukti klinis tersedia";
    case "pharmacopoeia":
      return "Farmakope/Materia Medika";
    case "review":
      return "Kajian literatur";
    case "preclinical":
      return "Praklinik";
    case "computational":
      return "Komputasional";
    default:
      return "Data bukti belum tersedia";
  }
}

export function dedupeSources(sources: SourceReference[]) {
  const seen = new Set<string>();
  return sources.filter((source) => {
    const key = source.source_id ?? source.identifier ?? source.title ?? JSON.stringify(source);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function collectRecommendationSources(item: HerbalRecommendationItem) {
  const enrichment = item.enrichment ?? {};
  const sources: SourceReference[] = [...(item.evidence_sources ?? []), ...(item.sources ?? [])];

  for (const group of [
    item.traditional_uses ?? enrichment.traditional_uses,
    item.preparation_methods ?? enrichment.preparation_methods,
    item.usage_guidelines ?? enrichment.usage_guidelines,
    item.safety_warnings ?? enrichment.safety_warnings,
    item.clinical_guidelines ?? enrichment.clinical_guidelines,
    item.claims ?? enrichment.claims,
  ]) {
    for (const entry of group ?? []) sources.push(...(entry.sources ?? []));
  }

  return dedupeSources(sources);
}

export function isVisibleToPersona(visibleTo: string[] | undefined, persona: Persona) {
  return !visibleTo?.length || visibleTo.includes(persona);
}

export function clinicalDoseTextForPersona(text: string | null | undefined, persona: Persona) {
  if (!text) return null;
  if (persona === "tenaga_medis" || persona === "peneliti") return text;
  return "Dosis klinis detail tidak ditampilkan untuk penggunaan mandiri. Gunakan sesuai batas wajar dan konsultasikan kepada tenaga kesehatan bila memiliki kondisi khusus.";
}

export function getSafetyStatusLabel(status?: string) {
  switch (status) {
    case "safe":
      return "Relatif aman";
    case "limited":
      return "Data keamanan terbatas";
    case "caution":
      return "Perlu perhatian";
    case "unsafe":
      return "Tidak disarankan";
    default:
      return "Data keamanan belum cukup";
  }
}

export function getCandidateQualityLabel(score?: number | null) {
  if (typeof score !== "number" || !Number.isFinite(score)) {
    return "Data belum dapat dipastikan";
  }
  if (score >= 0.75) return "Kandidat utama";
  if (score >= 0.5) return "Kandidat relevan";
  if (score >= 0.25) return "Kandidat awal";
  return "Perlu verifikasi";
}

export function formatPercent(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Belum tersedia";
  return `${Math.round(Math.max(0, Math.min(value, 1)) * 100)}%`;
}

export function getApiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const data = error.response?.data;
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.message === "string") return data.message;
    if (typeof data?.error === "string") return data.error;
    if (typeof data?.detail?.message === "string") return data.detail.message;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Terjadi kesalahan tidak diketahui.";
}
