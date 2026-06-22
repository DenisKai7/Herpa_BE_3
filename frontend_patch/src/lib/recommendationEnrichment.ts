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

export function getCandidateQualityLabel(item: HerbalRecommendationItem) {
  // Prefer backend-provided data_status_label if available
  if (item.data_status_label) return item.data_status_label;

  const score = item.confidence ?? item.relevance_score ?? item.recommendation_score;
  const hasTraditional = (item.traditional_uses?.length ?? 0) > 0;
  const hasCompounds = (item.active_compounds?.length ?? 0) > 0;
  const hasSources = (item.evidence_sources?.length ?? 0) > 0 || (item.sources?.length ?? 0) > 0;

  if (hasSources) return "Data sumber tersedia";
  if (hasTraditional && hasCompounds) return "Didukung data knowledge graph";
  if (hasTraditional) return "Data tradisional tersedia";
  if (hasCompounds) return "Data senyawa tersedia";

  if (typeof score !== "number" || !Number.isFinite(score)) {
    return "Data masih terbatas";
  }
  if (score >= 0.75) return "Kandidat utama";
  if (score >= 0.5) return "Kandidat relevan";
  if (score >= 0.25) return "Kandidat awal";
  return "Perlu verifikasi";
}

export function getRelevanceLabel(score?: number | null): string {
  if (typeof score !== "number" || !Number.isFinite(score)) return "Relevansi belum tersedia";
  if (score >= 0.75) return "Relevansi tinggi";
  if (score >= 0.50) return "Relevansi sedang";
  if (score >= 0.25) return "Relevansi rendah";
  if (score > 0) return "Kandidat awal";
  return "Relevansi belum tersedia";
}

export function getRelevancePercent(item: HerbalRecommendationItem): number {
  // Use backend-provided relevance_percent if available
  if (typeof item.relevance_percent === "number") return item.relevance_percent;
  const score = item.relevance_score ?? item.confidence ?? item.recommendation_score ?? 0;
  return Math.round(Math.max(0, Math.min(score, 1)) * 100);
}

export function getRelevanceLabelForCard(item: HerbalRecommendationItem): string {
  // Use backend-provided relevance_label if available
  if (item.relevance_label) return item.relevance_label;
  const score = item.relevance_score ?? item.confidence ?? item.recommendation_score;
  return getRelevanceLabel(score);
}

export function getSymptomCoveragePercent(item: HerbalRecommendationItem): number {
  if (typeof item.symptom_coverage_percent === "number") return item.symptom_coverage_percent;
  const score = item.symptom_coverage ?? item.primary_coverage_score ?? 0;
  return Math.round(Math.max(0, Math.min(score, 1)) * 100);
}

export function getSafetyLabelForCard(item: HerbalRecommendationItem): string {
  // Use backend-provided safety_label if available
  if (item.safety_label) return item.safety_label;
  return getSafetyStatusLabel(item.safety_status);
}

export function getEvidenceLabelForCard(item: HerbalRecommendationItem): string {
  // Use backend-provided evidence_label if available
  if (item.evidence_label) return item.evidence_label;
  return getEvidenceLabel(item.evidence_status);
}

export function getPlantPartDisplay(item: HerbalRecommendationItem): string {
  const parts = item.plant_parts ?? item.enrichment?.plant_parts ?? [];
  const names = parts.map((p) => p.name).filter(Boolean);
  if (names.length > 0) return names.join(", ");
  return "Bagian tanaman belum tersedia pada knowledge graph.";
}

export function getAvailabilityDisplay(item: HerbalRecommendationItem): string {
  const guidelines = item.storage_guidelines ?? item.enrichment?.storage_guidelines ?? [];
  if (guidelines.length > 0) {
    return guidelines
      .map((g) => [g.title, g.description].filter(Boolean).join(": "))
      .join("; ");
  }
  return "Ketersediaan belum tercatat secara spesifik pada knowledge graph.";
}

export function getPreparationDisplay(item: HerbalRecommendationItem): string {
  const methods = item.preparation_methods ?? item.enrichment?.preparation_methods ?? [];
  if (methods.length > 0) {
    return methods
      .map((m) => {
        const parts = [m.title, m.method_type, m.plant_part].filter(Boolean);
        if (m.steps?.length) parts.push("Langkah: " + m.steps.join(", "));
        if (m.notes) parts.push("Catatan: " + m.notes);
        return parts.join(" — ");
      })
      .join("\n");
  }
  return "Cara pengolahan belum tercatat pada knowledge graph untuk kandidat ini.";
}

export function getUsageGuidelineDisplay(item: HerbalRecommendationItem): string {
  const guidelines = item.usage_guidelines ?? item.enrichment?.usage_guidelines ?? [];
  if (guidelines.length > 0) {
    return guidelines
      .map((g) => {
        const parts = [g.title, g.description, g.frequency_text, g.duration_text].filter(Boolean);
        return parts.join(" — ");
      })
      .join("\n");
  }
  return "Aturan pakai spesifik belum tercatat pada knowledge graph. Gunakan informasi herbal secara hati-hati dan konsultasikan dengan tenaga kesehatan bila gejala menetap.";
}

export function getSafetyDisplay(item: HerbalRecommendationItem): {
  warnings: string[];
  contraindications: string[];
  interactions: string[];
  populationRisks: string[];
  hasSafetyData: boolean;
  fallbackMessage: string;
} {
  const warnings = (item.safety_warnings ?? item.enrichment?.safety_warnings ?? [])
    .map((w) => [w.title, w.description].filter(Boolean).join(": "))
    .filter(Boolean);
  const contraindications = (item.contraindications_detail ?? item.enrichment?.contraindications ?? [])
    .map((c) => [c.condition, c.description].filter(Boolean).join(": "))
    .filter(Boolean);
  const interactions = (item.drug_interactions_detail ?? item.enrichment?.drug_interactions ?? [])
    .map((d) => [d.substance, d.description].filter(Boolean).join(": "))
    .filter(Boolean);
  const populationRisks: string[] = [];
  for (const w of item.safety_warnings ?? item.enrichment?.safety_warnings ?? []) {
    for (const r of w.population_risks ?? []) {
      if (r && !populationRisks.includes(r)) populationRisks.push(r);
    }
  }

  const hasSafetyData =
    warnings.length > 0 || contraindications.length > 0 || interactions.length > 0 || populationRisks.length > 0;

  return {
    warnings,
    contraindications,
    interactions,
    populationRisks,
    hasSafetyData,
    fallbackMessage:
      "Belum ada peringatan spesifik yang tercatat pada knowledge graph. Tetap berhati-hati bila sedang hamil, menyusui, memiliki penyakit kronis, atau menggunakan obat rutin.",
  };
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
