-- D1 schema for the Anima lead intake Worker. Apply once:
--   npx wrangler d1 execute anima-leads --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS leads (
  lead_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
  lead_id TEXT PRIMARY KEY REFERENCES leads(lead_id),
  status TEXT NOT NULL DEFAULT 'pending',   -- pending | sending | delivered | dead
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at INTEGER NOT NULL,
  claimed_at INTEGER,
  last_error TEXT,
  delivered_at INTEGER
);
CREATE INDEX IF NOT EXISTS outbox_due ON outbox(status, next_attempt_at);
CREATE TABLE IF NOT EXISTS rate (
  bucket TEXT NOT NULL,
  window INTEGER NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (bucket, window)
);
