import "server-only";
import fs from "fs";
import path from "path";
import type { EmailRecord } from "./types";

const STORE_PATH = path.join(process.cwd(), "data", "emails.json");

type Store = Record<string, EmailRecord>;

function readStore(): Store {
  try {
    const raw = fs.readFileSync(STORE_PATH, "utf-8");
    return JSON.parse(raw) as Store;
  } catch {
    return {};
  }
}

function writeStore(store: Store) {
  fs.mkdirSync(path.dirname(STORE_PATH), { recursive: true });
  fs.writeFileSync(STORE_PATH, JSON.stringify(store, null, 2), "utf-8");
}

export function getEmailRecord(domain: string): EmailRecord | undefined {
  const store = readStore();
  return store[domain];
}

export function saveEmailRecord(record: EmailRecord) {
  const store = readStore();
  store[record.domain] = record;
  writeStore(store);
  return record;
}

export function getAllEmailRecords(): Store {
  return readStore();
}
