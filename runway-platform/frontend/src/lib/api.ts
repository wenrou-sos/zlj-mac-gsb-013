import type {
  AnalyzeResult,
  AutoResolveResult,
  Closure,
  Flight,
  Runway,
  SeparationMatrix,
} from "./types";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listRunways: () => req<Runway[]>("/api/runways"),
  createRunway: (r: Runway) => req<Runway>("/api/runways", {
    method: "POST",
    body: JSON.stringify(r),
  }),
  deleteRunway: (id: string) =>
    req<void>(`/api/runways/${encodeURIComponent(id)}`, { method: "DELETE" }),

  listFlights: () => req<Flight[]>("/api/flights"),
  createFlight: (f: Flight) => req<Flight>("/api/flights", {
    method: "POST",
    body: JSON.stringify(f),
  }),
  updateFlight: (id: string, f: Flight) =>
    req<Flight>(`/api/flights/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(f),
    }),
  deleteFlight: (id: string) =>
    req<void>(`/api/flights/${encodeURIComponent(id)}`, { method: "DELETE" }),

  listClosures: () => req<Closure[]>("/api/closures"),
  createClosure: (c: Closure) => req<Closure>("/api/closures", {
    method: "POST",
    body: JSON.stringify(c),
  }),
  deleteClosure: (id: string) =>
    req<void>(`/api/closures/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  getSeparation: () =>
    req<{ matrix: SeparationMatrix }>("/api/separation"),
  updateSeparation: (matrix: SeparationMatrix) =>
    req<{ matrix: SeparationMatrix }>("/api/separation", {
      method: "PUT",
      body: JSON.stringify({ matrix }),
    }),

  analyze: () => req<AnalyzeResult>("/api/analyze", { method: "POST" }),
  autoResolve: () =>
    req<AutoResolveResult>("/api/auto-resolve", { method: "POST" }),
};
