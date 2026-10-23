import { makeRequest } from "../utils/api";

const get = (path, signal) =>
  makeRequest(`/admin${path}`, {
    signal: signal ?? AbortSignal.timeout(20000),
  });
export const adminService = {
  metrics: (signal) => get("/analytics/dashboard", signal),
  logs: (signal) => get("/monitoring/audit-logs", signal),
  alerts: (signal) => get("/monitoring/fraud-alerts", signal),
  events: (filters, signal) =>
    get(`/events?${new URLSearchParams(filters)}`, signal),
  deleteEvent: (id) =>
    makeRequest(`/admin/events/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  users: (filters, signal) =>
    get(`/users?${new URLSearchParams(filters)}`, signal),
  updateUser: (id, action, body) =>
    makeRequest(`/admin/users/${encodeURIComponent(id)}/${action}`, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(20000),
    }),
};
