export type Operation = "arrival" | "departure";

export interface Runway {
  id: string;
  name: string;
  active: boolean;
}

export interface RouteStep {
  name: string;
  type: "runway" | "taxiway";
  runway_id?: string | null;
  primary?: boolean;
  crossing_duration?: number;
  taxi_seconds?: number;
  enter_offset?: number | null;
  vacate_offset?: number | null;
}

export interface Flight {
  id: string;
  callsign: string;
  operation: Operation;
  runway_id: string;
  scheduled_time?: string | null;
  takeoff_time?: string | null;
  landing_time?: string | null;
  enter_offset: number;
  vacate_offset: number;
  route: RouteStep[];
  aircraft_category?: string;
}

export interface Closure {
  id: string;
  runway_id: string;
  start_time: string;
  end_time: string;
  reason?: string;
}

export type ConflictType =
  | "SEPARATION"
  | "OCCUPANCY"
  | "CROSSING"
  | "CLOSURE";

export interface Conflict {
  id: string;
  type: ConflictType;
  runway_id: string;
  flight_ids: string[];
  message: string;
  time: string;
  severity: "high" | "medium" | "low";
  actual_gap_seconds?: number;
  required_gap_seconds?: number;
  closure_id?: string;
  window_start?: string;
  window_end?: string;
}

export interface ResolutionOption {
  kind: "DELAY" | "CHANGE_RUNWAY";
  delta_seconds?: number;
  new_runway_id?: string;
  description: string;
  residual_conflicts?: number;
}

export interface Resolution {
  flight_id: string;
  callsign: string;
  conflict_ids: string[];
  options: ResolutionOption[];
}

export interface AnalyzeResult {
  conflicts: Conflict[];
  resolutions: Resolution[];
}

export interface Adjustment {
  flight_id: string;
  callsign: string;
  delta_seconds: number;
}

export interface AutoResolveResult {
  flights: Flight[];
  adjustments: Adjustment[];
  total_delay_seconds: number;
  remaining_conflicts: Conflict[];
}

export type SeparationMatrix = Record<
  Operation,
  Partial<Record<Operation, number>>
>;
