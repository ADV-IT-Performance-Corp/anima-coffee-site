-- One physical database per tenant/environment. No customer data in logs.
CREATE TABLE IF NOT EXISTS leads (
 tenant TEXT NOT NULL CHECK(tenant = 'anima-coffee'),
 idem TEXT NOT NULL, id TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
 payload TEXT, state TEXT NOT NULL DEFAULT 'queued'
 CHECK(state IN ('queued','sending','unknown','roistat_accepted','kommo_confirmed','expired')),
 created INTEGER NOT NULL, expires INTEGER NOT NULL, next_attempt INTEGER NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0, proxy_id TEXT, kommo_id TEXT,
 PRIMARY KEY(tenant, idem)
);
CREATE INDEX IF NOT EXISTS leads_due ON leads(state,next_attempt);
CREATE INDEX IF NOT EXISTS leads_expiry ON leads(expires);
