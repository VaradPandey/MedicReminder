import axios from "axios";

const rawBase = import.meta.env.VITE_API_BASE_URL || "/api";
const apiBase = rawBase.endsWith("/api") || rawBase === "/api"
  ? rawBase
  : `${rawBase.replace(/\/+$/, "")}/api`;

const api = axios.create({
  baseURL: apiBase,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;