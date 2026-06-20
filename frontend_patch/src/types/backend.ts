export type Persona = "umum" | "pelajar" | "peneliti" | "tenaga_medis";
export type ApplicationRole = "admin" | "user";

export type SourceReference = {
  type?: string;
  source_id?: string | null;
  title?: string | null;
  identifier?: string | null;
  year?: string | number | null;
  evidence_level?: string | null;
  url?: string | null;
};

export type TraditionalUseItem = {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  category?: string | null;
  evidence_level?: string;
  verification_status?: string;
  recommendation_weight?: number | null;
  sources?: SourceReference[];
};

export type PreparationMethodItem = {
  id?: string | null;
  title?: string | null;
  method_type?: string | null;
  plant_part?: string | null;
  ingredients?: string[];
  steps?: string[];
  notes?: string | null;
  verification_status?: string;
  formulations?: string[];
  sources?: SourceReference[];
};

export type UsageGuidelineItem = {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  frequency_text?: string | null;
  duration_text?: string | null;
  dose_status?: string;
  verification_status?: string;
  sources?: SourceReference[];
};

export type SafetyWarningItem = {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  severity?: string;
  verification_status?: string;
  population_risks?: string[];
  sources?: SourceReference[];
};

export type PlantPartItem = { id?: string | null; name?: string | null; description?: string | null };
export type StorageGuidelineItem = { id?: string | null; title?: string | null; description?: string | null; storage_temperature?: string | null; notes?: string | null; verification_status?: string };
export type MythFactItem = { id?: string | null; claim?: string | null; fact?: string | null; risk_level?: string | null; verification_status?: string };
export type QualityStandardItem = { id?: string | null; parameter?: string | null; value?: string | null; source_standard?: string | null; verification_status?: string };
export type ClinicalGuidelineItem = { id?: string | null; mechanism?: string | null; therapeutic_dose_text?: string | null; notes?: string | null; visible_to?: string[]; sources?: SourceReference[] };
export type DrugInteractionItem = { id?: string | null; substance?: string | null; description?: string | null; severity?: string; population_risks?: string[] };
export type ContraindicationItem = { id?: string | null; condition?: string | null; description?: string | null; severity?: string; population_risks?: string[] };
export type PharmacokineticProfileItem = { absorption?: string | null; distribution?: string | null; metabolism?: string | null; excretion?: string | null };
export type ResearchTopicItem = { id?: string | null; title?: string | null; category?: string | null; visible_to?: string[] };
export type ClaimEvidenceItem = { claim_id?: string | null; claim_text?: string | null; claim_type?: string | null; evidence_level?: string; evidence_summary?: string | null; sources?: SourceReference[] };
export type SymptomItem = { id?: string | null; name?: string | null; category?: string | null; aliases?: string[] };

export type HerbEnrichmentDetail = {
  traditional_uses?: TraditionalUseItem[];
  preparation_methods?: PreparationMethodItem[];
  usage_guidelines?: UsageGuidelineItem[];
  safety_warnings?: SafetyWarningItem[];
  plant_parts?: PlantPartItem[];
  storage_guidelines?: StorageGuidelineItem[];
  myth_facts?: MythFactItem[];
  quality_standards?: QualityStandardItem[];
  clinical_guidelines?: ClinicalGuidelineItem[];
  drug_interactions?: DrugInteractionItem[];
  contraindications?: ContraindicationItem[];
  pharmacokinetic_profiles?: PharmacokineticProfileItem[];
  research_topics?: ResearchTopicItem[];
  claims?: ClaimEvidenceItem[];
  related_symptoms?: SymptomItem[];
};

export type HerbRecommendationDetailResponse = {
  status: string;
  herb_id: string;
  detail: HerbEnrichmentDetail;
  disclaimer: string;
};

export type HerbalRecommendationItem = {
  plant_id: string;
  herb_id?: string | null;
  local_name: string;
  scientific_name?: string | null;
  confidence?: number;
  relevance_score?: number;
  recommendation_score?: number;
  primary_coverage_score?: number;
  expanded_coverage_score?: number;
  traditional_use_score?: number;
  safety_score?: number;
  explanation?: string;
  recommendation_reason?: string;
  related_symptoms?: string[];
  active_compounds?: string[];
  safety_notes?: string[];
  warnings?: string[];
  evidence_sources?: SourceReference[];
  sources?: SourceReference[];
  enrichment?: HerbEnrichmentDetail;
  traditional_uses?: TraditionalUseItem[];
  preparation_methods?: PreparationMethodItem[];
  usage_guidelines?: UsageGuidelineItem[];
  safety_warnings?: SafetyWarningItem[];
  plant_parts?: PlantPartItem[];
  storage_guidelines?: StorageGuidelineItem[];
  myth_facts?: MythFactItem[];
  quality_standards?: QualityStandardItem[];
  clinical_guidelines?: ClinicalGuidelineItem[];
  drug_interactions_detail?: DrugInteractionItem[];
  contraindications_detail?: ContraindicationItem[];
  pharmacokinetic_profiles?: PharmacokineticProfileItem[];
  research_topics?: ResearchTopicItem[];
  claims?: ClaimEvidenceItem[];
  related_symptom_details?: SymptomItem[];
};

export interface ChatResponse {
  chat_id: string;
  response: string;
  quiz_data?: Record<string, unknown>;
  persona?: Persona;
  intent?: string;
  confidence?: number;
  grounding_status?: "grounded" | "partial" | "insufficient" | "safety_rule";
  sources: SourceReference[];
  warnings: string[];
}

export interface QuizCompletion {
  score: number;
  total_questions: number;
  accuracy: number;
  correct: number;
  incorrect: number;
  skipped: number;
  xp_earned: number;
  level_completed: boolean;
  next_level_unlocked: boolean;
  analisis_performa: { sorotan: string[]; area_fokus: string[] };
}
