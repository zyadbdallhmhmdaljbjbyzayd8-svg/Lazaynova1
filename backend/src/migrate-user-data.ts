import dotenv from "dotenv";
import { readFile } from "node:fs/promises";
import { getPool } from "./database.js";

dotenv.config();

const db = getPool();

if (!db) {
  throw new Error("DATABASE_URL is not configured");
}

const client = await db.connect();

try {
  await client.query("BEGIN");

  await client.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  const version = "002_user_data";
  const existing = await client.query(
    "SELECT version FROM schema_migrations WHERE version = $1",
    [version]
  );

  if (existing.rowCount === 0) {
    const migration = await readFile(
      new URL("../migrations/002_user_data.sql", import.meta.url),
      "utf8"
    );

    await client.query(migration);
    await client.query(
      "INSERT INTO schema_migrations(version) VALUES ($1)",
      [version]
    );
    console.log("Migration 002_user_data completed.");
  } else {
    console.log("Migration 002_user_data already applied.");
  }

  await client.query("COMMIT");
} catch (error) {
  await client.query("ROLLBACK");
  console.error("User data migration failed:", error);
  process.exitCode = 1;
} finally {
  client.release();
  await db.end();
}
