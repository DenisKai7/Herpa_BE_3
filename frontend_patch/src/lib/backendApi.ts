import axios from "axios";
import type {
  HerbRecommendationDetailResponse,
  QuizDashboard,
  QuizHistoryResponse,
  QuizProgress,
  QuizSession,
  QuizSessionSummary,
  QuizTopic,
  StartQuizSessionPayload,
  SubmitQuizAnswerPayload,
  SubmitQuizAnswerResponse,
} from "../types/backend";

export const backendApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  timeout: 120_000,
});

backendApi.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function isUnauthorizedError(error: unknown) {
  return axios.isAxiosError(error) && error.response?.status === 401;
}

export const LOGIN_EXPIRED_MESSAGE = "Sesi login berakhir. Silakan login ulang.";

backendApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isUnauthorizedError(error) && typeof window !== "undefined") {
      window.localStorage.removeItem("access_token");
    }
    return Promise.reject(error);
  },
);

export async function getHerbRecommendationDetail(herbId: string) {
  const response = await backendApi.get<HerbRecommendationDetailResponse>(
    `/api/herbal-recommendations/herbs/${encodeURIComponent(herbId)}/detail`,
  );
  return response.data;
}

export async function getQuizDashboard() {
  const response = await backendApi.get<QuizDashboard>("/api/quiz/dashboard");
  return response.data;
}

export async function getQuizProgress() {
  const response = await backendApi.get<QuizProgress>("/api/quiz/progress");
  return response.data;
}

export async function getQuizTopics() {
  const response = await backendApi.get<{ topics: QuizTopic[] }>("/api/quiz/topics");
  return response.data;
}

export async function createQuizSession(payload: StartQuizSessionPayload) {
  const response = await backendApi.post<QuizSession>("/api/quiz/sessions", payload);
  return response.data;
}

export async function getQuizSession(attemptId: string) {
  const response = await backendApi.get<QuizSession>(`/api/quiz/sessions/${encodeURIComponent(attemptId)}`);
  return response.data;
}

export async function submitQuizAnswer(attemptId: string, payload: SubmitQuizAnswerPayload) {
  const response = await backendApi.post<SubmitQuizAnswerResponse>(
    `/api/quiz/sessions/${encodeURIComponent(attemptId)}/answer`,
    { elapsed_ms: 0, ...payload },
  );
  return response.data;
}

export async function getQuizSessionSummary(attemptId: string) {
  const response = await backendApi.get<QuizSessionSummary>(`/api/quiz/sessions/${encodeURIComponent(attemptId)}/summary`);
  return response.data;
}

export async function getQuizHistory() {
  const response = await backendApi.get<QuizHistoryResponse>("/api/quiz/history");
  return response.data;
}
