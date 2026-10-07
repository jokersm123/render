CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;

ALTER TABLE users
ALTER COLUMN is_active SET DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_uq
ON users (LOWER(username));

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq
ON users (LOWER(email));
