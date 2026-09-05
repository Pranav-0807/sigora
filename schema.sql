CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    country VARCHAR(100) DEFAULT 'India',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    source VARCHAR(50) DEFAULT 'manual',
    currency VARCHAR(10) DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS budgets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    target_amount NUMERIC(12,2) NOT NULL,
    current_amount NUMERIC(12,2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'INR',
    target_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id
ON transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_date
ON transactions(date);

CREATE INDEX IF NOT EXISTS idx_budgets_user_id
ON budgets(user_id);

CREATE INDEX IF NOT EXISTS idx_goals_user_id
ON goals(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_unique
ON budgets(user_id, category, month, year);

-- Launch features / preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_email_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS budget_alerts_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_alerts_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_alerts_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_started_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_status VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_cancel_at_cycle_end BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS gamification (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    current_streak INTEGER NOT NULL DEFAULT 0,
    best_streak INTEGER NOT NULL DEFAULT 0,
    last_activity_date DATE,
    transactions_count INTEGER NOT NULL DEFAULT 0,
    budgets_created INTEGER NOT NULL DEFAULT 0,
    goals_created INTEGER NOT NULL DEFAULT 0,
    goals_completed INTEGER NOT NULL DEFAULT 0,
    badges TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    alert_type VARCHAR(30) NOT NULL DEFAULT 'info',
    link VARCHAR(255),
    fingerprint VARCHAR(255),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    announcement_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_alerts_user_created ON alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_announcement_id ON alerts(announcement_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_fingerprint
ON alerts(user_id, fingerprint) WHERE fingerprint IS NOT NULL;


CREATE TABLE IF NOT EXISTS ai_usage (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    month_start DATE NOT NULL,
    month_requests INTEGER NOT NULL DEFAULT 0,
    day_start DATE NOT NULL,
    day_requests INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_global_usage (
    month_start DATE PRIMARY KEY,
    requests INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS support_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(100),
    email VARCHAR(255) NOT NULL,
    issue_type VARCHAR(80) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id, created_at DESC);


CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(60) UNIQUE NOT NULL,
    discount_type VARCHAR(20) NOT NULL DEFAULT 'percent',
    discount_value NUMERIC(10,2) NOT NULL,
    max_uses INTEGER,
    uses INTEGER NOT NULL DEFAULT 0,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    first_month_only BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coupon_redemptions (
    coupon_id INTEGER REFERENCES coupons(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(coupon_id,user_id)
);


-- Currency migration for existing installations
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';
ALTER TABLE budgets ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';
ALTER TABLE goals ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';
UPDATE transactions t SET currency = COALESCE(t.currency, u.currency, 'INR') FROM users u WHERE u.id=t.user_id;
UPDATE budgets b SET currency = COALESCE(b.currency, u.currency, 'INR') FROM users u WHERE u.id=b.user_id;
UPDATE goals g SET currency = COALESCE(g.currency, u.currency, 'INR') FROM users u WHERE u.id=g.user_id;

CREATE TABLE IF NOT EXISTS financial_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(40) NOT NULL,
    provider_account_id VARCHAR(180),
    institution_name VARCHAR(180) NOT NULL,
    account_name VARCHAR(180),
    account_type VARCHAR(60),
    country VARCHAR(80) NOT NULL DEFAULT 'India',
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    masked_account VARCHAR(40),
    balance NUMERIC(18,2),
    status VARCHAR(30) NOT NULL DEFAULT 'connected',
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_financial_accounts_user ON financial_accounts(user_id);

CREATE TABLE IF NOT EXISTS bank_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(40) NOT NULL,
    consent_id VARCHAR(180) UNIQUE,
    data_session_id VARCHAR(180),
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    consent_expires_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bank_connections_user ON bank_connections(user_id);

CREATE TABLE IF NOT EXISTS external_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    financial_account_id INTEGER REFERENCES financial_accounts(id) ON DELETE SET NULL,
    provider VARCHAR(40) NOT NULL,
    external_id VARCHAR(240) NOT NULL,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider, external_id)
);
CREATE INDEX IF NOT EXISTS idx_external_transactions_user ON external_transactions(user_id);

-- Investment intelligence / portfolio tracking
CREATE TABLE IF NOT EXISTS investor_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    objective VARCHAR(40) NOT NULL DEFAULT 'growth',
    horizon_years INTEGER NOT NULL DEFAULT 5,
    risk_comfort VARCHAR(20) NOT NULL DEFAULT 'moderate',
    loss_reaction VARCHAR(30) NOT NULL DEFAULT 'hold',
    emergency_months NUMERIC(6,2) NOT NULL DEFAULT 0,
    monthly_investment NUMERIC(18,2) NOT NULL DEFAULT 0,
    profile VARCHAR(20) NOT NULL DEFAULT 'Moderate',
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS investments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    symbol VARCHAR(40),
    asset_type VARCHAR(40) NOT NULL,
    sector VARCHAR(100),
    quantity NUMERIC(20,6) NOT NULL DEFAULT 0,
    average_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    current_price NUMERIC(18,4) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_investments_user ON investments(user_id);
CREATE TABLE IF NOT EXISTS investment_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    symbol VARCHAR(40),
    asset_type VARCHAR(40) NOT NULL DEFAULT 'Stock',
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON investment_watchlist(user_id);

-- Admin V1
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(30) NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason TEXT;
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(account_status);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    details TEXT,
    ip_address VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at DESC);

CREATE TABLE IF NOT EXISTS admin_login_attempts (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255),
    ip_address VARCHAR(80),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_lookup ON admin_login_attempts(email, ip_address, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_notes (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_announcements (
    id BIGSERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    title_ta VARCHAR(180),
    message_ta TEXT,
    title_hi VARCHAR(180),
    message_hi TEXT,
    link VARCHAR(255),
    audience VARCHAR(30) NOT NULL DEFAULT 'all',
    recipients INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    system_key VARCHAR(80)
);
ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS system_key VARCHAR(80);
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_announcements_system_key
ON admin_announcements(system_key) WHERE system_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS payment_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    payment_id VARCHAR(120),
    order_id VARCHAR(120),
    subscription_id VARCHAR(120),
    amount NUMERIC(18,2),
    currency VARCHAR(10),
    status VARCHAR(60),
    source VARCHAR(30) NOT NULL DEFAULT 'webhook',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_payment_events_created ON payment_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_events_user ON payment_events(user_id);
