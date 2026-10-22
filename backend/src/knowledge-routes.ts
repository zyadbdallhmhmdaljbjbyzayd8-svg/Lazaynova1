import { Router } from "express";
import { z } from "zod";

import {
  indexDocument,
  searchKnowledge,
  listKnowledge,
  deleteKnowledgeDocument
} from "./knowledge.js";

import { runReasoning } from "./reasoning.js";

export const knowledgeRouter = Router();

const indexSchema = z.object({
  title: z.string().trim().min(1).max(200),
  text: z.string().trim().min(1).max(500_000),
  source: z.string().trim().max(500).optional()
});

const searchSchema = z.object({
  query: z.string().trim().min(1).max(12_000),
  limit: z.coerce.number().int().min(1).max(10).optional()
});

const reasonSchema = z.object({
  question: z.string().trim().min(1).max(12_000)
});

knowledgeRouter.get("/documents", (_req, res) => {
  res.json({
    documents: listKnowledge()
  });
});

knowledgeRouter.post("/index", (req, res) => {
  const parsed = indexSchema.safeParse(req.body);

  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid document",
      details: parsed.error.flatten()
    });
    return;
  }

  try {
    const result = indexDocument(parsed.data);

    res.status(201).json({
      ok: true,
      ...result
    });
  } catch (error) {
    res.status(400).json({
      error: error instanceof Error
        ? error.message
        : "Indexing failed"
    });
  }
});

knowledgeRouter.post("/search", (req, res) => {
  const parsed = searchSchema.safeParse(req.body);

  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid search request",
      details: parsed.error.flatten()
    });
    return;
  }

  res.json({
    results: searchKnowledge(
      parsed.data.query,
      parsed.data.limit ?? 5
    )
  });
});

knowledgeRouter.delete("/documents/:id", (req, res) => {
  const id = req.params.id;

  if (!id || id.length > 100) {
    res.status(400).json({ error: "Invalid document ID" });
    return;
  }

  const deleted = deleteKnowledgeDocument(id);

  if (!deleted) {
    res.status(404).json({ error: "Document not found" });
    return;
  }

  res.json({ ok: true, deleted: true });
});

knowledgeRouter.post("/reason", async (req, res) => {
  const parsed = reasonSchema.safeParse(req.body);

  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid reasoning request",
      details: parsed.error.flatten()
    });
    return;
  }

  try {
    const result = await runReasoning(parsed.data.question);
    res.json(result);
  } catch (error) {
    res.status(502).json({
      error: "Reasoning engine unavailable",
      detail: error instanceof Error
        ? error.message
        : "Unknown error"
    });
  }
});
