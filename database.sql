-- ========================================================
-- TimberOps Stock Tracker Database
-- ========================================================

CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    item_code TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,

    specification TEXT NOT NULL DEFAULT '',

    quantity INTEGER NOT NULL DEFAULT 0
        CHECK (quantity >= 0),

    minimum_level INTEGER NOT NULL DEFAULT 0
        CHECK (minimum_level >= 0),

    unit TEXT NOT NULL DEFAULT 'units',
    location TEXT NOT NULL DEFAULT '',

    unit_cost REAL NOT NULL DEFAULT 0
        CHECK (unit_cost >= 0),

    notes TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS stock_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stock_item_id INTEGER NOT NULL,

    movement_type TEXT NOT NULL,

    amount INTEGER NOT NULL
        CHECK (amount > 0),

    previous_quantity INTEGER NOT NULL
        CHECK (previous_quantity >= 0),

    new_quantity INTEGER NOT NULL
        CHECK (new_quantity >= 0),

    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,

    FOREIGN KEY (stock_item_id)
        REFERENCES stock_items(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    job_number TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL DEFAULT '',
    customer_email TEXT NOT NULL DEFAULT '',

    job_title TEXT NOT NULL,
    job_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',

    site_address TEXT NOT NULL DEFAULT '',
    suburb TEXT NOT NULL DEFAULT '',

    priority TEXT NOT NULL DEFAULT 'Normal',
    status TEXT NOT NULL DEFAULT 'Received',

    received_date TEXT NOT NULL,
    scheduled_date TEXT NOT NULL DEFAULT '',

    start_time TEXT NOT NULL DEFAULT '',
    end_time TEXT NOT NULL DEFAULT '',

    estimated_hours REAL NOT NULL DEFAULT 0
        CHECK (estimated_hours >= 0),

    assigned_to TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_jobs_scheduled_date
    ON jobs (scheduled_date);


CREATE INDEX IF NOT EXISTS idx_jobs_status
    ON jobs (status);


CREATE INDEX IF NOT EXISTS idx_jobs_customer
    ON jobs (customer_name);


CREATE INDEX IF NOT EXISTS idx_jobs_number
    ON jobs (job_number);