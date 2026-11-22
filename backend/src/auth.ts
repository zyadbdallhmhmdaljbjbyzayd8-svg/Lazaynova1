import { Router, type RequestHandler } from "express";
import { OAuth2Client } from "google-auth-library";
import { SignJWT, jwtVerify } from "jose";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { getPool } from "./database.js";

const router = Router();
const googleClient = new OAuth2Client();

const hashToken = (token: string) =>
  createHash("sha256").update(token).digest("hex");

function getAuthConfig() {
  const clientId = process.env.GOOGLE_WEB_CLIENT_ID;
  const secret = process.env.JWT_ACCESS_SECRET;

  if (!clientId || !secret || secret.length < 32) {
    throw new Error("Authentication is not configured");
  }

  return { clientId, secret: new TextEncoder().encode(secret) };
}

async function createAccessToken(userId: string, email: string) {
  const { secret } = getAuthConfig();

  return new SignJWT({ email })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(userId)
    .setIssuedAt()
    .setExpirationTime("15m")
    .sign(secret);
}

function createRefreshToken() {
  return randomBytes(48).toString("base64url");
}

async function saveRefreshToken(
  client: import("pg").PoolClient,
  userId: string,
  token: string
) {
  await client.query(
    `INSERT INTO refresh_sessions
      (id, user_id, token_hash, expires_at, created_at)
     VALUES ($1, $2, $3, NOW() + INTERVAL '30 days', NOW())`,
    [randomUUID(), userId, hashToken(token)]
  );
}

export const requireAuth: RequestHandler = async (req, res, next) => {
  try {
    const header = req.headers.authorization;
    const token = header?.startsWith("Bearer ")
      ? header.slice(7)
      : "";

    if (!token) {
      res.status(401).json({ error: "Authentication required" });
      return;
    }

    const { secret } = getAuthConfig();
    const verified = await jwtVerify(token, secret, {
      algorithms: ["HS256"]
    });

    if (!verified.payload.sub) {
      res.status(401).json({ error: "Invalid access token" });
      return;
    }

    res.locals.userId = verified.payload.sub;
    next();
  } catch {
    res.status(401).json({ error: "Invalid or expired access token" });
  }
};

router.post("/google", async (req, res) => {
  const db = getPool();

  if (!db) {
    res.status(503).json({ error: "Database is not configured" });
    return;
  }

  let client: import("pg").PoolClient | undefined;

  try {
    const { clientId } = getAuthConfig();
    const idToken = req.body?.idToken;

    if (typeof idToken !== "string" || !idToken) {
      res.status(400).json({ error: "Google ID token is required" });
      return;
    }

    const ticket = await googleClient.verifyIdToken({
      idToken,
      audience: clientId
    });

    const payload = ticket.getPayload();

    if (
      !payload?.sub ||
      !payload.email ||
      payload.email_verified !== true
    ) {
      res.status(401).json({ error: "Google account is not verified" });
      return;
    }

    client = await db.connect();
    await client.query("BEGIN");

    const userResult = await client.query<{
      id: string;
      email: string;
      display_name: string | null;
      avatar_url: string | null;
    }>(
      `INSERT INTO users
        (id, google_sub, email, display_name, avatar_url, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
       ON CONFLICT (google_sub)
       DO UPDATE SET
         email = EXCLUDED.email,
         display_name = COALESCE(EXCLUDED.display_name, users.display_name),
         avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
         updated_at = NOW()
       RETURNING id, email, display_name, avatar_url`,
      [
        randomUUID(),
        payload.sub,
        payload.email,
        payload.name ?? null,
        payload.picture ?? null
      ]
    );

    const user = userResult.rows[0];
    const refreshToken = createRefreshToken();

    await saveRefreshToken(client, user.id, refreshToken);
    await client.query("COMMIT");

    const accessToken = await createAccessToken(user.id, user.email);

    res.json({
      accessToken,
      refreshToken,
      expiresIn: 900,
      user
    });
  } catch (error) {
    if (client) await client.query("ROLLBACK").catch(() => undefined);
    console.error("[auth/google] Authentication failed:", error);
    res.status(500).json({ error: "Google authentication failed" });
  } finally {
    client?.release();
  }
});

router.post("/refresh", async (req, res) => {
  const db = getPool();

  if (!db) {
    res.status(503).json({ error: "Database is not configured" });
    return;
  }

  const oldToken = req.body?.refreshToken;

  if (typeof oldToken !== "string" || !oldToken) {
    res.status(400).json({ error: "Refresh token is required" });
    return;
  }

  let client: import("pg").PoolClient | undefined;

  try {
    client = await db.connect();
    await client.query("BEGIN");

    const result = await client.query<{
      id: string;
      user_id: string;
      email: string;
    }>(
      `SELECT rs.id, rs.user_id, u.email
       FROM refresh_sessions rs
       JOIN users u ON u.id = rs.user_id
       WHERE rs.token_hash = $1
         AND rs.revoked_at IS NULL
         AND rs.expires_at > NOW()
       FOR UPDATE OF rs`,
      [hashToken(oldToken)]
    );

    const session = result.rows[0];

    if (!session) {
      await client.query("ROLLBACK");
      res.status(401).json({ error: "Refresh token is invalid or expired" });
      return;
    }

    await client.query(
      "UPDATE refresh_sessions SET revoked_at = NOW() WHERE id = $1",
      [session.id]
    );

    const refreshToken = createRefreshToken();
    await saveRefreshToken(client, session.user_id, refreshToken);
    await client.query("COMMIT");

    const accessToken = await createAccessToken(
      session.user_id,
      session.email
    );

    res.json({ accessToken, refreshToken, expiresIn: 900 });
  } catch (error) {
    if (client) await client.query("ROLLBACK").catch(() => undefined);
    console.error("[auth/refresh] Session refresh failed:", error);
    res.status(500).json({ error: "Session refresh failed" });
  } finally {
    client?.release();
  }
});

router.post("/logout", async (req, res) => {
  const db = getPool();
  const refreshToken = req.body?.refreshToken;

  if (!db) {
    res.status(503).json({ error: "Database is not configured" });
    return;
  }

  if (typeof refreshToken !== "string" || !refreshToken) {
    res.status(400).json({ error: "Refresh token is required" });
    return;
  }

  try {
    await db.query(
      `UPDATE refresh_sessions
       SET revoked_at = NOW()
       WHERE token_hash = $1 AND revoked_at IS NULL`,
      [hashToken(refreshToken)]
    );

    res.json({ success: true });
  } catch (error) {
    console.error("[auth/logout] Logout failed:", error);
    res.status(500).json({ error: "Logout failed" });
  }
});

router.get("/me", requireAuth, async (_req, res) => {
  const db = getPool();

  if (!db) {
    res.status(503).json({ error: "Database is not configured" });
    return;
  }

  try {
    const result = await db.query(
      `SELECT id, email, display_name, avatar_url, created_at
       FROM users WHERE id = $1`,
      [res.locals.userId]
    );

    if (!result.rows[0]) {
      res.status(404).json({ error: "User not found" });
      return;
    }

    res.json({ user: result.rows[0] });
  } catch (error) {
    console.error("[auth/me] User lookup failed:", error);
    res.status(500).json({ error: "Could not load user" });
  }
});

export default router;
