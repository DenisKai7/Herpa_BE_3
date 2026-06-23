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
  relevance_level?: string;
  relevance_label?: string;
  relevance_percent?: number;
  symptom_coverage?: number;
  symptom_coverage_percent?: number;
  data_status?: string;
  data_status_label?: string;
  safety_status?: string;
  safety_label?: string;
  evidence_status?: string;
  evidence_label?: string;
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

export type HerbalRecommendationResponse = {
  status: string;
  request_id?: string | null;
  complaint?: string;
  normalized_complaint?: string;
  symptoms?: string[];
  extracted_symptoms?: string[];
  recommendations?: HerbalRecommendationItem[];
  options?: HerbalRecommendationItem[];
  red_flags?: string[];
  when_to_seek_medical_help?: string[];
  limitations?: string[];
  warnings?: string[];
  suggested_terms?: string[];
  medical_attention_message?: string | null;
  disclaimer?: string;
  general_disclaimer?: string;
  safety_note?: string;
  metadata?: Record<string, unknown>;
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

export type QuizQuestionType = "multiple_choice" | "matching" | "true_false" | "short_answer" | "case_based" | "case_study";

export type QuizMatchingItem = {
  key: string;
  text: string;
};

export type QuizMatchingPairs = {
  left_items: QuizMatchingItem[];
  right_items: QuizMatchingItem[];
};

export type QuizOption = {
  id: string;
  label: string;
  text: string;
};

export type QuizQuestion = {
  id: string;
  topic_id: string;
  level_id: string;
  question_type: QuizQuestionType;
  prompt: string;
  options: QuizOption[];
  matching_pairs: QuizMatchingPairs | unknown[];
  left_items?: QuizMatchingItem[];
  right_items?: QuizMatchingItem[];
  matching_prompt?: string | null;
  difficulty: string;
};

export type QuizLevel = {
  id: string;
  topic_id: string;
  level_number: number;
  title: string;
  description?: string | null;
  quiz_type: string;
  xp_reward: number;
  passing_score: number;
  is_locked: boolean;
  is_completed: boolean;
  progress: number;
};

export type QuizTopic = {
  id: string;
  title: string;
  description?: string | null;
  order_index?: number;
  icon?: string | null;
  progress: number;
  highest_level_completed: number;
  current_level: number;
  status: string;
  levels: QuizLevel[];
};

export type QuizProgress = {
  total_xp: number;
  level: number;
  completed_topics: number;
  completed_levels: number;
  current_streak: number;
  topic_progress: Record<string, unknown>[];
};

export type QuizSession = {
  id: string;
  topic_id: string;
  level_id: string;
  status: "active" | "completed" | string;
  score: number;
  total_questions: number;
  current_question_index: number;
  questions: QuizQuestion[];
};

export type StartQuizSessionPayload = {
  topic_id: string;
  level_id?: string | null;
  level_number?: number | null;
};

export type SubmitQuizAnswerPayload = {
  question_id: string;
  selected_option_id?: string | null;
  answer_text?: string | null;
  matching_answer?: Record<string, string>;
  elapsed_ms?: number;
  answer?: unknown;
};

export type SubmitQuizAnswerResponse = {
  correct: boolean;
  is_correct: boolean;
  question_type?: QuizQuestionType;
  answer_text?: string | null;
  correct_answer?: unknown;
  accepted_answers?: unknown[];
  formatted_correct_answer?: string | null;
  explanation?: string | null;
  score_delta: number;
  xp_delta: number;
  session_completed: boolean;
  session_score: number;
  correct_count: number;
  wrong_count: number;
  total_questions: number;
  next_question_index?: number | null;
  passed?: boolean | null;
  next_level_unlocked: boolean;
};

export type QuizHistoryItem = {
  session_id: string;
  id: string;
  topic_id: string;
  topic_title: string;
  level_id: string;
  level_number: number;
  quiz_type: string;
  score: number;
  xp_earned: number;
  status: "active" | "completed" | string;
  passed: boolean;
  started_at?: string | null;
  completed_at?: string | null;
};

export type QuizHistoryResponse = { history: QuizHistoryItem[] };

export type QuizSessionSummary = Omit<QuizHistoryItem, "id" | "started_at" | "completed_at"> & {
  correct_count: number;
  wrong_count: number;
  total_questions: number;
  next_level_unlocked: boolean;
  next_level_number?: number | null;
  explanations: Array<{
    question_id: string;
    prompt?: string;
    user_answer?: unknown;
    correct_answer?: unknown;
    is_correct: boolean;
    explanation?: string | null;
  }>;
};

export type QuizDashboard = {
  progress: QuizProgress;
  topics: QuizTopic[];
  active_sessions: QuizHistoryItem[];
};
