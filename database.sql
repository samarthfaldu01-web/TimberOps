-- ========================================================
-- File: database.sql
-- Project: TimberOps
--
-- Purpose:
-- Creates the tables used by the Stock Tracker.
-- ========================================================


-- Stores the current information for each stock item.
CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    item_code TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 0
        CHECK (quantity >= 0),

    minimum_level INTEGER NOT NULL DEFAULT 0
        CHECK (minimum_level >= 0),

    unit TEXT NOT NULL DEFAULT 'units',
    location TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


-- Stores a history of stock being checked in or checked out.
CREATE TABLE IF NOT EXISTS stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stock_item_id INTEGER NOT NULL,

    movement_type TEXT NOT NULL
        CHECK (
            movement_type IN (
                'Initial Stock',
                'Stock In',
                'Stock Out',
                'Edited'
            )
        ),

    amount INTEGER NOT NULL
        CHECK (amount >= 0),

    previous_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,

    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,

    FOREIGN KEY (stock_item_id)
        REFERENCES stock_items(id)
        ON DELETE CASCADE
);
