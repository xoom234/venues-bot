export interface Venue {
  row: number;
  name: string;
  status: string;
  aroma: string;
  format: string;
}

export type Filter = "all" | "passed" | "failed";

export type Screen =
  | { name: "list" }
  | { name: "detail"; venue: Venue }
  | { name: "add" }
  | { name: "aroma"; venue: Venue }
  | { name: "format"; venue: Venue };
