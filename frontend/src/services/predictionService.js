import { apiFetch, PIPELINE_API_URL } from '../utils/api';

const hasValue = (value) =>
  value !== "" && value !== null && value !== undefined;
async function responseError(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return new Error(body.detail);
  } catch {
    /* Non-JSON gateway response. */
  }
  return new Error(`Prediction service returned ${response.status}`);
}
async function request(path, params = {}, options = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => hasValue(value)),
  );
  const response = await apiFetch(
    `${PIPELINE_API_URL}${path}${query.size ? `?${query}` : ""}`,
    {
      ...options,
      cache: "no-store",
      signal: options.signal ?? AbortSignal.timeout(20000),
    },
  );
  if (!response.ok) throw await responseError(response);
  return response.json();
}
export const predictionService = {
  getBettingIntel(sport, signal) {
    return request(`/betting-intel${sport ? `/${encodeURIComponent(sport)}` : ''}`, {}, { signal });
  },
  getOperations(signal) {
    return request("/prediction-dashboard/operations", {}, { signal });
  },
  getPaperTrials(signal) {
    return request("/prediction-dashboard/paper-trials", {}, { signal });
  },
  getMatches(filters = {}, options = {}) {
    return request("/matches", filters, options);
  },
  getDashboard(filters, signal) {
    return request("/prediction-dashboard/fixtures", filters, { signal });
  },
  getHistory(filters, signal) {
    return request("/predictions/history-data", filters, { signal });
  },
  getAccuracy(filters, signal) {
    return request("/predictions/accuracy-data", filters, { signal });
  },
  getVersions(signal) {
    return request("/predictions/versions", {}, { signal });
  },
  getSportModels(signal) {
    return request("/sport-models", {}, { signal });
  },
  getSportModelTeams(filters, signal) {
    return request("/sport-models/teams", filters, { signal });
  },
  previewSportModel(body) {
    return request(
      "/sport-models/preview",
      {},
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(45000),
      },
    );
  },
};
