import { randomUUID } from "node:crypto";
import { getPool } from "./database.js";

function database() {
  const db = getPool();
  if (!db) throw new Error("Database is not configured");
  return db;
}

export async function createConversation(
  userId: string,
  title: string,
  engineId = "chat"
) {
  const id = randomUUID();
  const result = await database().query(
    `INSERT INTO conversations (id, user_id, title, engine_id)
     VALUES ($1, $2, $3, $4)
     RETURNING id, title, engine_id, created_at, updated_at`,
    [id, userId, title.trim().slice(0, 200) || "محادثة جديدة", engineId]
  );
  return result.rows[0];
}

export async function listConversations(userId: string) {
  const result = await database().query(
    `SELECT id, title, engine_id, created_at, updated_at
     FROM conversations
     WHERE user_id = $1 AND archived_at IS NULL
     ORDER BY updated_at DESC
     LIMIT 100`,
    [userId]
  );
  return result.rows;
}

export async function getConversation(userId: string, conversationId: string) {
  const result = await database().query(
    `SELECT id, title, engine_id, created_at, updated_at
     FROM conversations
     WHERE id = $1 AND user_id = $2 AND archived_at IS NULL`,
    [conversationId, userId]
  );
  return result.rows[0] ?? null;
}

export async function listMessages(
  userId: string,
  conversationId: string
) {
  const result = await database().query(
    `SELECT id, role, content, engine_id, metadata, created_at
     FROM messages
     WHERE conversation_id = $1 AND user_id = $2
     ORDER BY created_at ASC
     LIMIT 500`,
    [conversationId, userId]
  );
  return result.rows;
}

export async function addMessage(input: {
  userId: string;
  conversationId: string;
  role: "user" | "assistant" | "system";
  content: string;
  engineId?: string;
  metadata?: Record<string, unknown>;
}) {
  const db = database();
  const client = await db.connect();

  try {
    await client.query("BEGIN");

    const owned = await client.query(
      `UPDATE conversations
       SET updated_at = NOW()
       WHERE id = $1 AND user_id = $2 AND archived_at IS NULL
       RETURNING id`,
      [input.conversationId, input.userId]
    );

    if (owned.rowCount !== 1) {
      throw new Error("Conversation not found");
    }

    const result = await client.query(
      `INSERT INTO messages
       (id, conversation_id, user_id, role, content, engine_id, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
       RETURNING id, role, content, engine_id, metadata, created_at`,
      [
        randomUUID(),
        input.conversationId,
        input.userId,
        input.role,
        input.content,
        input.engineId ?? null,
        JSON.stringify(input.metadata ?? {})
      ]
    );

    await client.query("COMMIT");
    return result.rows[0];
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function archiveConversation(
  userId: string,
  conversationId: string
) {
  const result = await database().query(
    `UPDATE conversations
     SET archived_at = NOW(), updated_at = NOW()
     WHERE id = $1 AND user_id = $2 AND archived_at IS NULL
     RETURNING id`,
    [conversationId, userId]
  );
  return (result.rowCount ?? 0) === 1;
}

export async function getPreferences(userId: string) {
  const result = await database().query(
    `SELECT theme, language, settings, updated_at
     FROM user_preferences WHERE user_id = $1`,
    [userId]
  );

  return result.rows[0] ?? {
    theme: "system",
    language: "ar",
    settings: {}
  };
}

export async function savePreferences(
  userId: string,
  input: {
    theme?: "light" | "dark" | "system";
    language?: string;
    settings?: Record<string, unknown>;
  }
) {
  const current = await getPreferences(userId);
  const theme = input.theme ?? current.theme;
  const language = input.language ?? current.language;
  const settings = input.settings ?? current.settings;

  if (!["light", "dark", "system"].includes(theme)) {
    throw new Error("Invalid theme");
  }

  if (typeof language !== "string" || language.length < 2 || language.length > 10) {
    throw new Error("Invalid language");
  }

  const result = await database().query(
    `INSERT INTO user_preferences
      (user_id, theme, language, settings, updated_at)
     VALUES ($1, $2, $3, $4::jsonb, NOW())
     ON CONFLICT (user_id) DO UPDATE SET
       theme = EXCLUDED.theme,
       language = EXCLUDED.language,
       settings = EXCLUDED.settings,
       updated_at = NOW()
     RETURNING theme, language, settings, updated_at`,
    [userId, theme, language, JSON.stringify(settings)]
  );

  return result.rows[0];
}

export async function saveKnowledgeDocument(
  userId: string,
  title: string,
  content: string
) {
  if (!title.trim()) throw new Error("Document title is required");
  if (!content.trim()) throw new Error("Document content is required");
  if (content.length > 500_000) throw new Error("Document is too large");

  const result = await database().query(
    `INSERT INTO knowledge_documents (id, user_id, title, content)
     VALUES ($1, $2, $3, $4)
     RETURNING id, title, created_at`,
    [randomUUID(), userId, title.trim().slice(0, 200), content]
  );
  return result.rows[0];
}

export async function searchKnowledgeDocuments(
  userId: string,
  query: string,
  limit = 10
) {
  const safeLimit = Math.max(1, Math.min(20, Math.floor(limit)));
  const result = await database().query(
    `SELECT id, title,
       LEFT(content, 12000) AS content,
       created_at, updated_at
     FROM knowledge_documents
     WHERE user_id = $1
       AND (title ILIKE $2 OR content ILIKE $2)
     ORDER BY updated_at DESC
     LIMIT $3`,
    [userId, `%${query.trim().slice(0, 200)}%`, safeLimit]
  );
  return result.rows;
}

export async function listKnowledgeDocuments(userId: string) {
  const result = await database().query(
    `SELECT id, title, created_at, updated_at,
       LENGTH(content) AS character_count
     FROM knowledge_documents
     WHERE user_id = $1
     ORDER BY updated_at DESC
     LIMIT 100`,
    [userId]
  );
  return result.rows;
}

export async function deleteKnowledgeDocumentForUser(
  userId: string,
  documentId: string
) {
  const result = await database().query(
    `DELETE FROM knowledge_documents
     WHERE id = $1 AND user_id = $2
     RETURNING id`,
    [documentId, userId]
  );
  return (result.rowCount ?? 0) === 1;
}
