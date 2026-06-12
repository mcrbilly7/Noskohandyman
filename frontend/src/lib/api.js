import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  timeout: 30000,
});

// Uploads can be large (phone photos) and storage may be slow — give them their own timeout.
export const uploadApi = axios.create({
  baseURL: API,
  withCredentials: true,
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nosko_session_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fileUrl = (path) => (path ? `${API}/files/${path}` : "");
