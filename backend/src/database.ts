import pg from "pg";

const { Pool } = pg;
let pool: pg.Pool | null = null;

export function getPool(): pg.Pool | null {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) return null;

  if (!pool) {
    pool = new Pool({
      connectionString,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
      ssl: process.env.PGSSL === "true"
        ? { rejectUnauthorized: true }
        : undefined
    });
  }

  return pool;
}
