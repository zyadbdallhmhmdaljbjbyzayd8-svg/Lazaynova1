import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export type KnowledgeChunk = {
  id: string;
  documentId: string;
  title: string;
  source: string;
  text: string;
  terms: string[];
  createdAt: string;
};

const DATA_DIR = process.env.LAZAYNOVA_DATA_DIR
  || path.resolve(process.cwd(), "data");

const DB_FILE = path.join(DATA_DIR, "knowledge.json");

function ensureDb(): void {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(DB_FILE)) {
    fs.writeFileSync(DB_FILE, "[]", "utf8");
  }
}

function readDb(): KnowledgeChunk[] {
  ensureDb();

  try {
    const value: unknown = JSON.parse(
      fs.readFileSync(DB_FILE, "utf8")
    );

    if (!Array.isArray(value)) {
      throw new Error("Knowledge database must be an array");
    }

    return value as KnowledgeChunk[];
  } catch (error) {
    throw new Error(
      `Cannot read knowledge database: ${
        error instanceof Error ? error.message : "unknown error"
      }`
    );
  }
}

function writeDb(items: KnowledgeChunk[]): void {
  ensureDb();

  const temporary = `${DB_FILE}.${process.pid}.tmp`;

  fs.writeFileSync(
    temporary,
    JSON.stringify(items, null, 2),
    "utf8"
  );

  fs.renameSync(temporary, DB_FILE);
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[\u064B-\u065F\u0670]/g, "")
    .replace(/[أإآ]/g, "ا")
    .replace(/ى/g, "ي")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function tokenize(text: string): string[] {
  return normalize(text)
    .split(/\s+/)
    .filter((word) => word.length > 1);
}

function splitIntoChunks(
  text: string,
  chunkSize = 900,
  overlap = 120
): string[] {
  const cleaned = text.replace(/\r\n/g, "\n").trim();

  if (!cleaned) return [];

  const chunks: string[] = [];
  let start = 0;

  while (start < cleaned.length) {
    let end = Math.min(start + chunkSize, cleaned.length);

    if (end < cleaned.length) {
      const boundary = cleaned.lastIndexOf(" ", end);
      if (boundary > start + chunkSize * 0.6) {
        end = boundary;
      }
    }

    const part = cleaned.slice(start, end).trim();

    if (part) chunks.push(part);
    if (end >= cleaned.length) break;

    start = Math.max(start + 1, end - overlap);
  }

  return chunks;
}

export function indexDocument(input: {
  title: string;
  text: string;
  source?: string;
}): {
  documentId: string;
  chunksIndexed: number;
} {
  if (!input.title.trim()) {
    throw new Error("Document title is required");
  }

  if (!input.text.trim()) {
    throw new Error("Document text is required");
  }

  if (input.text.length > 500_000) {
    throw new Error("Document exceeds 500000 characters");
  }

  const documentId = crypto.randomUUID();
  const now = new Date().toISOString();

  const chunks = splitIntoChunks(input.text).map(
    (text): KnowledgeChunk => ({
      id: crypto.randomUUID(),
      documentId,
      title: input.title.trim().slice(0, 200),
      source: (input.source || input.title).slice(0, 500),
      text,
      terms: [...new Set(tokenize(text))],
      createdAt: now
    })
  );

  writeDb([...readDb(), ...chunks]);

  return {
    documentId,
    chunksIndexed: chunks.length
  };
}

function scoreChunk(
  queryTerms: string[],
  chunk: KnowledgeChunk
): number {
  if (queryTerms.length === 0) return 0;

  const terms = new Set(chunk.terms);
  const titleTerms = new Set(tokenize(chunk.title));

  let matched = 0;
  let titleMatched = 0;

  for (const term of new Set(queryTerms)) {
    if (terms.has(term)) matched++;
    if (titleTerms.has(term)) titleMatched++;
  }

  const coverage = matched / new Set(queryTerms).size;
  const titleBoost = titleMatched > 0 ? 0.15 : 0;

  return Math.min(1, coverage + titleBoost);
}

export function searchKnowledge(
  query: string,
  limit = 5
): Array<KnowledgeChunk & { score: number }> {
  const queryTerms = tokenize(query);

  if (queryTerms.length === 0) return [];

  const safeLimit = Math.max(1, Math.min(10, Math.floor(limit)));

  return readDb()
    .map((chunk) => ({
      ...chunk,
      score: scoreChunk(queryTerms, chunk)
    }))
    .filter((chunk) => chunk.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, safeLimit);
}

export function listKnowledge(): Array<{
  documentId: string;
  title: string;
  source: string;
  chunks: number;
}> {
  const groups = new Map<string, {
    documentId: string;
    title: string;
    source: string;
    chunks: number;
  }>();

  for (const chunk of readDb()) {
    const existing = groups.get(chunk.documentId);

    if (existing) {
      existing.chunks++;
    } else {
      groups.set(chunk.documentId, {
        documentId: chunk.documentId,
        title: chunk.title,
        source: chunk.source,
        chunks: 1
      });
    }
  }

  return [...groups.values()];
}

export function deleteKnowledgeDocument(
  documentId: string
): boolean {
  const items = readDb();
  const remaining = items.filter(
    (item) => item.documentId !== documentId
  );

  if (remaining.length === items.length) return false;

  writeDb(remaining);
  return true;
}
