import axios from "axios";
import type { HerbRecommendationDetailResponse } from "../types/backend";

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

backendApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
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
