export interface Company {
  score: number;
  run: string;
  niche: string;
  nicheSource: string;
  nicheConfidence: number;
  company: string;
  domain: string;
  segment: string;
  revenueEur: string;
  employees: string;
  googleAds: boolean;
  convTracking: boolean;
  metaPixel: boolean;
  qualityIssues: number;
  issueFlags: string[];
  platform: string;
  email: string;
  phone: string;
  city: string;
  googleVerifiedLive: boolean;
  googleAdvertiserName: string;
  adsStatus: string;
  hasAnalysis: boolean;
}

export interface EmailRecord {
  domain: string;
  emails: string[];
  phone?: string;
  source: "csv" | "scrape";
  scrapedAt?: string;
  pagesChecked?: string[];
  error?: string;
}

export type SegmentFilter = "all" | "A" | "B" | "C";
export type BooleanFilter = "all" | "yes" | "no";
