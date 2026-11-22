import dotenv from "dotenv";
import { Pool } from "pg";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

dotenv.config();

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error("DATABASE_URL is not configured.");
  process.exit(1);
}

const pool = new Pool({
  connectionString,
  ssl: process.env.PGSSL === "true"
    ? { rejectUnauthorized: true }
    : undefined
});

try {
  const migration = await readFile(
    join(process.cwd(), "migrations", "001_auth.sql"),
    "utf8"
  );

  await pool.query(migration);
  console.log("Database migration 001_auth completed.");
} catch (error) {
  console.error("Database migration failed:", error);
  process.exitCode = 1;
} finally {
  await pool.end();
}
