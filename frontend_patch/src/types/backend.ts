export type Persona = "umum" | "pelajar" | "peneliti" | "tenaga_medis";
export type ApplicationRole = "admin" | "user";

export interface SourceReference {
  type: "neo4j" | "pubmed" | "pubchem" | "attachment" | string;
  source_id: string;
  title: string;
  url?: string;
  evidence_level?: string;
}

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
