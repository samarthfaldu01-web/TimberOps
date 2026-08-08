from __future__ import annotations

import calendar
import csv
import hmac
import io
import os
import re
import secrets
import sqlite3

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


# ==========================================================
# APPLICATION CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "timberops.db"

SCHEMA_PATH = BASE_DIR / "database.sql"


app = Flask(__name__)


app.config.update(
    SECRET_KEY=os.environ.get(
        "TIMBEROPS_SECRET_KEY",
        "TimberOps2026"
    ),

    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# ==========================================================
# STOCK TRACKER OPTIONS
# ==========================================================

CATEGORIES = (
    "Structural Timber",
    "Dressed Timber",
    "Decking Timber",
    "Sheet Materials",
    "Hardware and Fixings",
    "Adhesives",
    "Finishes and Coatings",
    "Abrasives",
    "Hand Tools",
    "Power Tools",
    "Tool Accessories",
    "Safety Equipment",
)


UNITS = (
    "lengths",
    "boards",
    "sheets",
    "pieces",
    "packs",
    "boxes",
    "units",
    "litres",
    "tubes",
    "rolls",
    "kilograms",
)


SORT_OPTIONS = {
    "updated_desc":
        "updated_at DESC, id DESC",

    "name_asc":
        "item_name COLLATE NOCASE ASC",

    "name_desc":
        "item_name COLLATE NOCASE DESC",

    "quantity_asc":
        "quantity ASC, item_name COLLATE NOCASE ASC",

    "quantity_desc":
        "quantity DESC, item_name COLLATE NOCASE ASC",

    "value_desc":
        "(quantity * unit_cost) DESC, "
        "item_name COLLATE NOCASE ASC",

    "code_asc":
        "item_code COLLATE NOCASE ASC",
}


# ==========================================================
# JOB SCHEDULING OPTIONS
# ==========================================================

JOB_TYPES = (
    "Custom Furniture",
    "Cabinetry",
    "Joinery",
    "Decking",
    "Timber Framing",
    "Door Installation",
    "Window Installation",
    "Repairs and Maintenance",
    "Fit-Out",
    "Renovation",
    "On-Site Installation",
    "Other",
)


JOB_PRIORITIES = (
    "Low",
    "Normal",
    "High",
    "Urgent",
)


JOB_STATUSES = (
    "Received",
    "Accepted",
    "Scheduled",
    "In Progress",
    "On Hold",
    "Completed",
    "Cancelled",
)


# ==========================================================
# DATABASE
# ==========================================================

def db() -> sqlite3.Connection:
    """
    Returns one SQLite database connection
    for the current Flask request.
    """

    if "db" not in g:

        g.db = sqlite3.connect(
            DB_PATH
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    """
    Closes the database after each request.
    """

    connection = g.pop(
        "db",
        None
    )

    if connection is not None:
        connection.close()


def columns(table: str) -> set[str]:
    """
    Returns the current columns in a database table.
    """

    return {
        row["name"]

        for row in db().execute(
            f"PRAGMA table_info({table})"
        )
    }


def add_column(
    table: str,
    name: str,
    definition: str
):
    """
    Safely adds a missing column to an existing table.
    """

    if name not in columns(table):

        db().execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {name} {definition}
            """
        )


def init_db():
    """
    Loads the existing TimberOps database schema
    and safely upgrades it for Job Requests and
    Job Scheduling.

    Existing stock data is not deleted.
    """

    if SCHEMA_PATH.exists():

        db().executescript(
            SCHEMA_PATH.read_text(
                encoding="utf-8"
            )
        )


    # ------------------------------------------------------
    # CORE TABLES
    # ------------------------------------------------------

    db().executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_code TEXT NOT NULL UNIQUE,

            item_name TEXT NOT NULL,

            category TEXT NOT NULL,

            specification
                TEXT NOT NULL DEFAULT '',

            quantity
                INTEGER NOT NULL DEFAULT 0,

            minimum_level
                INTEGER NOT NULL DEFAULT 0,

            unit
                TEXT NOT NULL DEFAULT 'units',

            location
                TEXT NOT NULL DEFAULT '',

            unit_cost
                REAL NOT NULL DEFAULT 0,

            notes
                TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS stock_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            stock_item_id INTEGER NOT NULL,

            movement_type TEXT NOT NULL,

            amount INTEGER NOT NULL,

            previous_quantity INTEGER NOT NULL,

            new_quantity INTEGER NOT NULL,

            reason
                TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,

            FOREIGN KEY (stock_item_id)
                REFERENCES stock_items(id)
                ON DELETE CASCADE
        );


        CREATE TABLE IF NOT EXISTS job_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            request_number
                TEXT NOT NULL UNIQUE,

            customer_name
                TEXT NOT NULL,

            customer_email
                TEXT NOT NULL,

            customer_phone
                TEXT NOT NULL,

            job_title
                TEXT NOT NULL,

            job_type
                TEXT NOT NULL,

            description
                TEXT NOT NULL,

            site_address
                TEXT NOT NULL,

            suburb
                TEXT NOT NULL,

            preferred_date
                TEXT NOT NULL DEFAULT '',

            preferred_start_time
                TEXT NOT NULL DEFAULT '',

            preferred_end_time
                TEXT NOT NULL DEFAULT '',

            priority
                TEXT NOT NULL DEFAULT 'Normal',

            notes
                TEXT NOT NULL DEFAULT '',

            status
                TEXT NOT NULL DEFAULT 'Pending',

            admin_note
                TEXT NOT NULL DEFAULT '',

            job_id INTEGER,

            decision_at
                TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_number
                TEXT NOT NULL UNIQUE,

            request_id INTEGER,

            customer_name
                TEXT NOT NULL,

            customer_phone
                TEXT NOT NULL DEFAULT '',

            customer_email
                TEXT NOT NULL DEFAULT '',

            job_title
                TEXT NOT NULL,

            job_type
                TEXT NOT NULL,

            description
                TEXT NOT NULL DEFAULT '',

            site_address
                TEXT NOT NULL DEFAULT '',

            suburb
                TEXT NOT NULL DEFAULT '',

            priority
                TEXT NOT NULL DEFAULT 'Normal',

            status
                TEXT NOT NULL DEFAULT 'Accepted',

            received_date
                TEXT NOT NULL,

            scheduled_date
                TEXT NOT NULL DEFAULT '',

            start_time
                TEXT NOT NULL DEFAULT '',

            end_time
                TEXT NOT NULL DEFAULT '',

            estimated_hours
                REAL NOT NULL DEFAULT 0,

            assigned_to
                TEXT NOT NULL DEFAULT '',

            notes
                TEXT NOT NULL DEFAULT '',

            google_event_id
                TEXT NOT NULL DEFAULT '',

            google_sync_status
                TEXT NOT NULL DEFAULT 'Not connected',

            accepted_at
                TEXT NOT NULL DEFAULT '',

            completed_at
                TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            FOREIGN KEY (request_id)
                REFERENCES job_requests(id)
                ON DELETE SET NULL
        );


        CREATE INDEX IF NOT EXISTS
            idx_stock_activity_item
            ON stock_activity(stock_item_id);


        CREATE INDEX IF NOT EXISTS
            idx_job_requests_status
            ON job_requests(status);


        CREATE INDEX IF NOT EXISTS
            idx_jobs_status
            ON jobs(status);


        CREATE INDEX IF NOT EXISTS
            idx_jobs_date
            ON jobs(scheduled_date);
        """
    )


    # ------------------------------------------------------
    # SAFE UPGRADES FOR EXISTING STOCK TABLE
    # ------------------------------------------------------

    add_column(
        "stock_items",
        "specification",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_column(
        "stock_items",
        "unit_cost",
        "REAL NOT NULL DEFAULT 0"
    )


    # ------------------------------------------------------
    # SAFE UPGRADES FOR EXISTING JOBS TABLE
    # ------------------------------------------------------

    job_upgrades = {
        "request_id":
            "INTEGER",

        "google_event_id":
            "TEXT NOT NULL DEFAULT ''",

        "google_sync_status":
            "TEXT NOT NULL DEFAULT 'Not connected'",

        "accepted_at":
            "TEXT NOT NULL DEFAULT ''",

        "completed_at":
            "TEXT NOT NULL DEFAULT ''",
    }


    for column_name, definition in job_upgrades.items():

        add_column(
            "jobs",
            column_name,
            definition
        )


    db().commit()


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def now() -> str:
    """
    Returns a database-friendly timestamp.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def login_required(view):
    """
    Prevents unauthorised users from accessing
    administrator pages.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get(
            "admin_logged_in"
        ):

            flash(
                "Please log in to access TimberOps.",
                "error"
            )

            return redirect(
                url_for("admin_login")
            )

        return view(
            *args,
            **kwargs
        )

    return wrapped


# ==========================================================
# CSRF SECURITY
# ==========================================================

def csrf_token() -> str:
    """
    Creates a CSRF token for forms.
    """

    if "csrf_token" not in session:

        session[
            "csrf_token"
        ] = secrets.token_urlsafe(
            32
        )

    return session[
        "csrf_token"
    ]


app.jinja_env.globals[
    "csrf_token"
] = csrf_token


def validate_csrf():
    """
    Validates forms that use CSRF protection.
    """

    submitted = request.form.get(
        "csrf_token",
        ""
    )

    saved = session.get(
        "csrf_token",
        ""
    )

    if (
        not submitted
        or not saved
        or not hmac.compare_digest(
            submitted,
            saved
        )
    ):

        abort(
            400,
            description=(
                "Invalid or missing security token."
            )
        )


# ==========================================================
# GENERAL ROUTES
# ==========================================================

@app.route("/")
def index():

    if session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("home")
        )

    return redirect(
        url_for("admin_login")
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        expected_user = os.environ.get(
            "TIMBEROPS_ADMIN_EMAIL",
            "admin@timberops.com"
        )


        expected_password = os.environ.get(
            "TIMBEROPS_ADMIN_PASSWORD",
            "TimberOps2026"
        )


        login_is_correct = (
            hmac.compare_digest(
                username,
                expected_user
            )

            and

            hmac.compare_digest(
                password,
                expected_password
            )
        )


        if login_is_correct:

            session.clear()

            session[
                "admin_logged_in"
            ] = True

            csrf_token()

            return redirect(
                url_for("home")
            )


        flash(
            "Invalid email or password.",
            "error"
        )


    return render_template(
        "admin_login.html"
    )


# ==========================================================
# FORGOT PASSWORD
# ==========================================================

@app.route("/forgot-password")
def forgot_password():

    return render_template(
        "forgot_password.html"
    )


# ==========================================================
# LOGOUT
# ==========================================================

@app.route(
    "/logout",
    methods=["POST"]
)
@login_required
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ==========================================================
# HOMEPAGE
# ==========================================================

@app.route("/home")
@login_required
def home():

    dashboard = db().execute(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stock_items
            )
            AS stock_records,

            (
                SELECT COUNT(*)
                FROM job_requests
                WHERE status = 'Pending'
            )
            AS pending_requests,

            (
                SELECT COUNT(*)
                FROM jobs
                WHERE scheduled_date = ?
                AND status NOT IN (
                    'Completed',
                    'Cancelled'
                )
            )
            AS jobs_today
        """,
        (
            date.today().isoformat(),
        )
    ).fetchone()


    return render_template(
        "homepage.html",
        dashboard=dashboard
    )


# ==========================================================
# STOCK TRACKER HELPERS
# ==========================================================

def get_stock_item(
    item_id: int
):

    return db().execute(
        """
        SELECT *
        FROM stock_items
        WHERE id = ?
        """,
        (
            item_id,
        )
    ).fetchone()


def validate_stock_form(
    form
):

    errors = []


    data = {
        "item_code":
            form.get(
                "item_code",
                ""
            ).strip().upper(),

        "item_name":
            form.get(
                "item_name",
                ""
            ).strip(),

        "category":
            form.get(
                "category",
                ""
            ).strip(),

        "specification":
            form.get(
                "specification",
                ""
            ).strip(),

        "unit":
            form.get(
                "unit",
                ""
            ).strip(),

        "location":
            form.get(
                "location",
                ""
            ).strip(),

        "notes":
            form.get(
                "notes",
                ""
            ).strip(),
    }


    try:

        data["quantity"] = int(
            form.get(
                "quantity",
                ""
            )
        )

    except (
        TypeError,
        ValueError
    ):

        data["quantity"] = 0

        errors.append(
            "Quantity must be a whole number."
        )


    try:

        data["minimum_level"] = int(
            form.get(
                "minimum_level",
                ""
            )
        )

    except (
        TypeError,
        ValueError
    ):

        data["minimum_level"] = 0

        errors.append(
            "Reorder level must be a whole number."
        )


    try:

        data["unit_cost"] = round(
            float(
                form.get(
                    "unit_cost",
                    "0"
                )
                or 0
            ),
            2
        )

    except (
        TypeError,
        ValueError
    ):

        data["unit_cost"] = 0.0

        errors.append(
            "Unit cost must be a valid number."
        )


    if not re.fullmatch(
        r"[A-Z0-9_-]{2,20}",
        data["item_code"]
    ):

        errors.append(
            "Item code must use 2-20 letters, "
            "numbers, hyphens or underscores."
        )


    if not 2 <= len(
        data["item_name"]
    ) <= 100:

        errors.append(
            "Item name must contain 2-100 characters."
        )


    if data[
        "category"
    ] not in CATEGORIES:

        errors.append(
            "Select a valid category."
        )


    if data[
        "unit"
    ] not in UNITS:

        errors.append(
            "Select a valid measurement unit."
        )


    if (
        data["quantity"] < 0
        or data["minimum_level"] < 0
        or data["unit_cost"] < 0
    ):

        errors.append(
            "Quantity, reorder level and "
            "unit cost cannot be negative."
        )


    if (
        len(
            data["specification"]
        ) > 200

        or len(
            data["location"]
        ) > 100

        or len(
            data["notes"]
        ) > 500
    ):

        errors.append(
            "One or more stock fields are too long."
        )


    return data, errors


def record_stock_activity(
    item_id,
    movement_type,
    amount,
    previous_quantity,
    new_quantity,
    reason
):

    db().execute(
        """
        INSERT INTO stock_activity (
            stock_item_id,
            movement_type,
            amount,
            previous_quantity,
            new_quantity,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            movement_type,
            amount,
            previous_quantity,
            new_quantity,
            reason,
            now()
        )
    )


def build_stock_filters(
    args
):

    search = args.get(
        "search",
        ""
    ).strip()

    category = args.get(
        "category",
        ""
    ).strip()

    status = args.get(
        "status",
        ""
    ).strip()

    sort = args.get(
        "sort",
        "updated_desc"
    ).strip()


    conditions = []

    params = []


    if search:

        pattern = (
            "%"
            + search.lower()
            + "%"
        )


        conditions.append(
            """
            (
                LOWER(item_code) LIKE ?
                OR LOWER(item_name) LIKE ?
                OR LOWER(category) LIKE ?
                OR LOWER(specification) LIKE ?
                OR LOWER(location) LIKE ?
                OR LOWER(notes) LIKE ?
            )
            """
        )


        params.extend(
            [pattern] * 6
        )


    if category in CATEGORIES:

        conditions.append(
            "category = ?"
        )

        params.append(
            category
        )


    if status == "available":

        conditions.append(
            "quantity > minimum_level"
        )


    elif status == "low":

        conditions.append(
            """
            quantity > 0
            AND quantity <= minimum_level
            """
        )


    elif status == "out":

        conditions.append(
            "quantity = 0"
        )


    if conditions:

        where_section = (
            " WHERE "
            + " AND ".join(
                conditions
            )
        )

    else:

        where_section = ""


    return {
        "search":
            search,

        "category":
            category,

        "status":
            status,

        "sort":
            sort,

        "where_section":
            where_section,

        "parameters":
            params,

        "order_section":
            SORT_OPTIONS.get(
                sort,
                SORT_OPTIONS[
                    "updated_desc"
                ]
            ),
    }


# ==========================================================
# STOCK SUPPLIER PLACEHOLDER
# ==========================================================

def search_google_suppliers(
    _item,
    _suburb
):
    """
    Google Places API is intentionally disabled
    until the API integration stage.
    """

    return (
        [],
        (
            "Supplier API is not connected yet. "
            "This feature is ready for the "
            "API integration stage."
        )
    )


# ==========================================================
# STOCK TRACKER PAGE
# ==========================================================

@app.route("/stock-tracker")
@login_required
def stock_tracker():

    filters = build_stock_filters(
        request.args
    )


    page = max(
        request.args.get(
            "page",
            1,
            type=int
        )
        or 1,
        1
    )


    per_page = 10


    total = db().execute(
        f"""
        SELECT COUNT(*)
        FROM stock_items
        {filters["where_section"]}
        """,
        filters["parameters"]
    ).fetchone()[0]


    total_pages = max(
        (
            total
            + per_page
            - 1
        )
        // per_page,
        1
    )


    page = min(
        page,
        total_pages
    )


    items = db().execute(
        f"""
        SELECT
            *,

            quantity * unit_cost
                AS stock_value,

            CASE
                WHEN quantity = 0
                    THEN 'Out of Stock'

                WHEN quantity <= minimum_level
                    THEN 'Low Stock'

                ELSE 'Available'
            END AS status_text,

            CASE
                WHEN quantity = 0
                    THEN 'out'

                WHEN quantity <= minimum_level
                    THEN 'low'

                ELSE 'available'
            END AS status_key

        FROM stock_items

        {filters["where_section"]}

        ORDER BY
            {filters["order_section"]}

        LIMIT ?
        OFFSET ?
        """,
        [
            *filters["parameters"],

            per_page,

            (
                page - 1
            ) * per_page
        ]
    ).fetchall()


    summary = db().execute(
        """
        SELECT
            COUNT(*)
                AS total_items,

            COALESCE(
                SUM(quantity),
                0
            )
                AS total_quantity,

            COALESCE(
                SUM(
                    quantity * unit_cost
                ),
                0
            )
                AS total_value,

            COALESCE(
                SUM(
                    CASE
                        WHEN quantity > 0
                        AND quantity <= minimum_level
                            THEN 1
                        ELSE 0
                    END
                ),
                0
            )
                AS low_items,

            COALESCE(
                SUM(
                    CASE
                        WHEN quantity = 0
                            THEN 1
                        ELSE 0
                    END
                ),
                0
            )
                AS out_items

        FROM stock_items
        """
    ).fetchone()


    activity = db().execute(
        """
        SELECT
            stock_activity.*,
            stock_items.item_name,
            stock_items.unit

        FROM stock_activity

        JOIN stock_items
            ON stock_items.id
            = stock_activity.stock_item_id

        ORDER BY
            stock_activity.id DESC

        LIMIT 12
        """
    ).fetchall()


    all_items = db().execute(
        """
        SELECT
            id,
            item_name,
            specification

        FROM stock_items

        ORDER BY
            item_name COLLATE NOCASE
        """
    ).fetchall()


    edit_item_id = request.args.get(
        "edit",
        type=int
    )


    adjust_item_id = request.args.get(
        "adjust",
        type=int
    )


    edit_item = (
        get_stock_item(
            edit_item_id
        )
        if edit_item_id
        else None
    )


    adjust_item = (
        get_stock_item(
            adjust_item_id
        )
        if adjust_item_id
        else None
    )


    suppliers = None

    supplier_error = None


    supplier_item_id = request.args.get(
        "supplier_item_id",
        type=int
    )


    supplier_suburb = request.args.get(
        "supplier_suburb",
        "Melbourne VIC"
    ).strip()


    if supplier_item_id:

        supplier_item = get_stock_item(
            supplier_item_id
        )


        if supplier_item:

            (
                suppliers,
                supplier_error
            ) = search_google_suppliers(
                supplier_item,
                supplier_suburb
            )


        else:

            supplier_error = (
                "The selected stock item "
                "no longer exists."
            )


    return render_template(
        "stock_tracker.html",

        items=items,

        all_items=all_items,

        activity=activity,

        summary=summary,

        categories=CATEGORIES,

        units=UNITS,

        filters=filters,

        page=page,

        total_pages=total_pages,

        total=total,

        show_add=(
            request.args.get(
                "panel"
            )
            == "add"
        ),

        edit_item=edit_item,

        adjust_item=adjust_item,

        suppliers=suppliers,

        supplier_error=supplier_error,

        supplier_item_id=supplier_item_id,

        supplier_suburb=supplier_suburb,
    )


# ==========================================================
# ADD STOCK
# ==========================================================

@app.route(
    "/stock-tracker/add",
    methods=["POST"]
)
@login_required
def add_stock():

    data, errors = validate_stock_form(
        request.form
    )


    if errors:

        for message in errors:

            flash(
                message,
                "error"
            )


        return redirect(
            url_for(
                "stock_tracker",
                panel="add"
            )
        )


    timestamp = now()


    try:

        cursor = db().execute(
            """
            INSERT INTO stock_items (
                item_code,
                item_name,
                category,
                specification,
                quantity,
                minimum_level,
                unit,
                location,
                unit_cost,
                notes,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                data["item_code"],
                data["item_name"],
                data["category"],
                data["specification"],
                data["quantity"],
                data["minimum_level"],
                data["unit"],
                data["location"],
                data["unit_cost"],
                data["notes"],
                timestamp,
                timestamp
            )
        )


        if data[
            "quantity"
        ] > 0:

            record_stock_activity(
                cursor.lastrowid,
                "Initial Stock",
                data["quantity"],
                0,
                data["quantity"],
                "Opening quantity"
            )


        db().commit()


    except sqlite3.IntegrityError:

        db().rollback()

        flash(
            "That item code already exists.",
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                panel="add"
            )
        )


    flash(
        (
            f'{data["item_name"]} '
            "was added to Current Stock."
        ),
        "success"
    )


    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# EDIT STOCK
# ==========================================================

@app.route(
    "/stock-tracker/<int:item_id>/edit",
    methods=["POST"]
)
@login_required
def edit_stock(
    item_id
):

    existing = get_stock_item(
        item_id
    )


    if existing is None:

        flash(
            "Stock item not found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )


    data, errors = validate_stock_form(
        request.form
    )


    if errors:

        for message in errors:

            flash(
                message,
                "error"
            )


        return redirect(
            url_for(
                "stock_tracker",
                edit=item_id
            )
        )


    try:

        db().execute(
            """
            UPDATE stock_items

            SET
                item_code = ?,
                item_name = ?,
                category = ?,
                specification = ?,
                quantity = ?,
                minimum_level = ?,
                unit = ?,
                location = ?,
                unit_cost = ?,
                notes = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                data["item_code"],
                data["item_name"],
                data["category"],
                data["specification"],
                data["quantity"],
                data["minimum_level"],
                data["unit"],
                data["location"],
                data["unit_cost"],
                data["notes"],
                now(),
                item_id
            )
        )


        if (
            existing["quantity"]
            != data["quantity"]
        ):

            record_stock_activity(
                item_id,
                "Edited Quantity",
                abs(
                    data["quantity"]
                    - existing["quantity"]
                ),
                existing["quantity"],
                data["quantity"],
                "Quantity changed in Edit Item"
            )


        db().commit()


    except sqlite3.IntegrityError:

        db().rollback()

        flash(
            (
                "That item code is "
                "already being used."
            ),
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                edit=item_id
            )
        )


    flash(
        (
            f'{data["item_name"]} '
            "was updated."
        ),
        "success"
    )


    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# STOCK IN / STOCK OUT
# ==========================================================

@app.route(
    "/stock-tracker/<int:item_id>/adjust",
    methods=["POST"]
)
@login_required
def adjust_stock(
    item_id
):

    item = get_stock_item(
        item_id
    )


    if item is None:

        flash(
            "Stock item not found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )


    movement = request.form.get(
        "movement",
        ""
    ).strip()


    reason = request.form.get(
        "reason",
        ""
    ).strip()[:300]


    try:

        amount = int(
            request.form.get(
                "amount",
                ""
            )
        )


    except (
        TypeError,
        ValueError
    ):

        amount = 0


    if (
        movement not in {
            "in",
            "out"
        }

        or amount <= 0
    ):

        flash(
            (
                "Choose Stock In or Stock Out "
                "and enter a positive quantity."
            ),
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                adjust=item_id
            )
        )


    previous = item[
        "quantity"
    ]


    if movement == "in":

        new_quantity = (
            previous
            + amount
        )

        label = "Stock In"


    else:

        new_quantity = (
            previous
            - amount
        )

        label = "Stock Out"


    if new_quantity < 0:

        flash(
            (
                "You cannot remove more stock "
                "than is currently available."
            ),
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                adjust=item_id
            )
        )


    db().execute(
        """
        UPDATE stock_items

        SET
            quantity = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            new_quantity,
            now(),
            item_id
        )
    )


    record_stock_activity(
        item_id,
        label,
        amount,
        previous,
        new_quantity,
        reason
    )


    db().commit()


    flash(
        (
            f"{label} saved for "
            f'{item["item_name"]}.'
        ),
        "success"
    )


    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# DELETE STOCK
# ==========================================================

@app.route(
    "/stock-tracker/<int:item_id>/delete",
    methods=["POST"]
)
@login_required
def delete_stock(
    item_id
):

    item = get_stock_item(
        item_id
    )


    if item is None:

        flash(
            "Stock item not found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )


    db().execute(
        """
        DELETE FROM stock_items
        WHERE id = ?
        """,
        (
            item_id,
        )
    )


    db().commit()


    flash(
        (
            f'{item["item_name"]} '
            "was deleted."
        ),
        "success"
    )


    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# STOCK CSV EXPORT
# ==========================================================

@app.route(
    "/stock-tracker/export.csv"
)
@login_required
def export_csv():

    filters = build_stock_filters(
        request.args
    )


    rows = db().execute(
        f"""
        SELECT
            item_code,
            item_name,
            category,
            specification,
            quantity,
            minimum_level,
            unit,
            location,
            unit_cost,

            quantity * unit_cost
                AS stock_value,

            notes,
            updated_at

        FROM stock_items

        {filters["where_section"]}

        ORDER BY
            {filters["order_section"]}
        """,
        filters["parameters"]
    ).fetchall()


    output = io.StringIO()


    writer = csv.writer(
        output
    )


    writer.writerow(
        [
            "Item Code",
            "Item Name",
            "Category",
            "Specification",
            "Quantity",
            "Reorder Level",
            "Unit",
            "Location",
            "Unit Cost AUD",
            "Stock Value AUD",
            "Notes",
            "Updated",
        ]
    )


    for row in rows:

        writer.writerow(
            list(row)
        )


    return Response(
        output.getvalue(),

        mimetype="text/csv",

        headers={
            "Content-Disposition":
                (
                    "attachment; "
                    "filename=timberops-stock.csv"
                )
        }
    )


# ==========================================================
# CUSTOMER JOB REQUEST HELPERS
# ==========================================================

def valid_date(
    value: str
) -> bool:

    try:

        datetime.strptime(
            value,
            "%Y-%m-%d"
        )

        return True


    except (
        TypeError,
        ValueError
    ):

        return False


def valid_time(
    value: str
) -> bool:

    try:

        datetime.strptime(
            value,
            "%H:%M"
        )

        return True


    except (
        TypeError,
        ValueError
    ):

        return False


def unique_number(
    prefix: str,
    table: str,
    column: str
) -> str:
    """
    Generates unique request/job references.
    """

    while True:

        value = (
            f"{prefix}-"
            f"{datetime.now():%Y%m%d}-"
            f"{secrets.token_hex(2).upper()}"
        )


        exists = db().execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE {column} = ?
            """,
            (
                value,
            )
        ).fetchone()


        if exists is None:

            return value


def validate_request(
    form
):

    errors = []


    data = {
        "customer_name":
            form.get(
                "customer_name",
                ""
            ).strip(),

        "customer_email":
            form.get(
                "customer_email",
                ""
            ).strip().lower(),

        "customer_phone":
            form.get(
                "customer_phone",
                ""
            ).strip(),

        "job_title":
            form.get(
                "job_title",
                ""
            ).strip(),

        "job_type":
            form.get(
                "job_type",
                ""
            ).strip(),

        "description":
            form.get(
                "description",
                ""
            ).strip(),

        "site_address":
            form.get(
                "site_address",
                ""
            ).strip(),

        "suburb":
            form.get(
                "suburb",
                ""
            ).strip(),

        "preferred_date":
            form.get(
                "preferred_date",
                ""
            ).strip(),

        "preferred_start_time":
            form.get(
                "preferred_start_time",
                ""
            ).strip(),

        "preferred_end_time":
            form.get(
                "preferred_end_time",
                ""
            ).strip(),

        "priority":
            form.get(
                "priority",
                "Normal"
            ).strip(),

        "notes":
            form.get(
                "notes",
                ""
            ).strip(),
    }


    if not 2 <= len(
        data["customer_name"]
    ) <= 100:

        errors.append(
            "Enter your full name."
        )


    if not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        data["customer_email"]
    ):

        errors.append(
            "Enter a valid email address."
        )


    if not 6 <= len(
        data["customer_phone"]
    ) <= 30:

        errors.append(
            "Enter a valid phone number."
        )


    if not 3 <= len(
        data["job_title"]
    ) <= 120:

        errors.append(
            (
                "Enter a short title for "
                "the requested work."
            )
        )


    if data[
        "job_type"
    ] not in JOB_TYPES:

        errors.append(
            "Select a valid service type."
        )


    if not 10 <= len(
        data["description"]
    ) <= 1500:

        errors.append(
            (
                "Job description must contain "
                "10-1500 characters."
            )
        )


    if (
        not 5 <= len(
            data["site_address"]
        ) <= 180

        or not 2 <= len(
            data["suburb"]
        ) <= 80
    ):

        errors.append(
            (
                "Enter a valid job site "
                "address and suburb/postcode."
            )
        )


    if data[
        "preferred_date"
    ]:

        if (
            not valid_date(
                data["preferred_date"]
            )

            or data[
                "preferred_date"
            ] < date.today().isoformat()
        ):

            errors.append(
                (
                    "Preferred date must "
                    "be today or later."
                )
            )


    start = data[
        "preferred_start_time"
    ]

    end = data[
        "preferred_end_time"
    ]


    if bool(start) != bool(end):

        errors.append(
            (
                "Enter both preferred start "
                "and end times, or leave both blank."
            )
        )


    if start:

        if (
            not valid_time(
                start
            )

            or not valid_time(
                end
            )

            or end <= start
        ):

            errors.append(
                (
                    "Enter a valid preferred "
                    "time range."
                )
            )


    if data[
        "priority"
    ] not in JOB_PRIORITIES:

        errors.append(
            "Select a valid urgency level."
        )


    if len(
        data["notes"]
    ) > 700:

        errors.append(
            (
                "Additional notes cannot "
                "exceed 700 characters."
            )
        )


    if not form.get(
        "privacy_acknowledgement"
    ):

        errors.append(
            (
                "Please acknowledge the privacy "
                "notice before submitting."
            )
        )


    return data, errors


def request_or_404(
    request_id: int
):

    row = db().execute(
        """
        SELECT *
        FROM job_requests
        WHERE id = ?
        """,
        (
            request_id,
        )
    ).fetchone()


    if row is None:

        abort(
            404,
            description=(
                "The selected job request "
                "does not exist."
            )
        )


    return row


def job_or_404(
    job_id: int
):

    row = db().execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (
            job_id,
        )
    ).fetchone()


    if row is None:

        abort(
            404,
            description=(
                "The selected job does not exist."
            )
        )


    return row


# ==========================================================
# PUBLIC CUSTOMER JOB REQUEST PAGE
# ==========================================================

@app.route(
    "/job-request",
    methods=["GET", "POST"]
)
def job_request():

    if request.method == "POST":

        validate_csrf()


        data, errors = validate_request(
            request.form
        )


        if errors:

            for message in errors:

                flash(
                    message,
                    "error"
                )


            return render_template(
                "job_request.html",

                job_types=JOB_TYPES,

                priorities=JOB_PRIORITIES,

                today=date.today().isoformat(),

                form_data=request.form,

                status_result=None,

                submitted_request=None,
            )


        reference = unique_number(
            "REQ",
            "job_requests",
            "request_number"
        )


        timestamp = now()


        db().execute(
            """
            INSERT INTO job_requests (
                request_number,
                customer_name,
                customer_email,
                customer_phone,
                job_title,
                job_type,
                description,
                site_address,
                suburb,
                preferred_date,
                preferred_start_time,
                preferred_end_time,
                priority,
                notes,
                status,
                admin_note,
                job_id,
                decision_at,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                reference,
                data["customer_name"],
                data["customer_email"],
                data["customer_phone"],
                data["job_title"],
                data["job_type"],
                data["description"],
                data["site_address"],
                data["suburb"],
                data["preferred_date"],
                data["preferred_start_time"],
                data["preferred_end_time"],
                data["priority"],
                data["notes"],
                "Pending",
                "",
                None,
                "",
                timestamp,
                timestamp
            )
        )


        db().commit()


        return redirect(
            url_for(
                "job_request",
                submitted=reference
            )
        )


    submitted_request = None


    submitted_reference = request.args.get(
        "submitted",
        ""
    ).strip().upper()


    if submitted_reference:

        submitted_request = db().execute(
            """
            SELECT
                request_number,
                job_title,
                job_type,
                preferred_date,
                status

            FROM job_requests

            WHERE request_number = ?
            """,
            (
                submitted_reference,
            )
        ).fetchone()


    return render_template(
        "job_request.html",

        job_types=JOB_TYPES,

        priorities=JOB_PRIORITIES,

        today=date.today().isoformat(),

        form_data={},

        status_result=None,

        submitted_request=submitted_request,
    )


# ==========================================================
# CUSTOMER REQUEST STATUS LOOKUP
# ==========================================================

@app.route(
    "/job-request/status",
    methods=["POST"]
)
def job_request_status():

    validate_csrf()


    reference = request.form.get(
        "request_number",
        ""
    ).strip().upper()


    email = request.form.get(
        "status_email",
        ""
    ).strip().lower()


    result = db().execute(
        """
        SELECT
            request_number,
            job_title,
            job_type,
            status,
            preferred_date,
            admin_note,
            updated_at

        FROM job_requests

        WHERE request_number = ?
        AND LOWER(customer_email) = ?
        """,
        (
            reference,
            email
        )
    ).fetchone()


    if result is None:

        flash(
            (
                "No matching request was found. "
                "Check the reference number and email."
            ),
            "error"
        )


    return render_template(
        "job_request.html",

        job_types=JOB_TYPES,

        priorities=JOB_PRIORITIES,

        today=date.today().isoformat(),

        form_data={},

        status_result=result,

        submitted_request=None,
    )


# ==========================================================
# CALENDAR BUILDER
# ==========================================================

def calendar_weeks(
    year: int,
    month: int
):

    calendar_builder = calendar.Calendar(
        firstweekday=0
    )


    raw_weeks = calendar_builder.monthdatescalendar(
        year,
        month
    )


    visible_start = (
        raw_weeks[0][0].isoformat()
    )


    visible_end = (
        raw_weeks[-1][-1].isoformat()
    )


    scheduled_jobs = db().execute(
        """
        SELECT *
        FROM jobs

        WHERE scheduled_date
            BETWEEN ? AND ?

        AND status <> 'Cancelled'

        ORDER BY
            scheduled_date,
            start_time,
            id
        """,
        (
            visible_start,
            visible_end
        )
    ).fetchall()


    jobs_by_date: dict[
        str,
        list[sqlite3.Row]
    ] = {}


    for job in scheduled_jobs:

        jobs_by_date.setdefault(
            job["scheduled_date"],
            []
        ).append(
            job
        )


    today = date.today()


    return [
        [
            {
                "iso":
                    calendar_date.isoformat(),

                "day_number":
                    calendar_date.day,

                "in_month":
                    calendar_date.month
                    == month,

                "is_today":
                    calendar_date
                    == today,

                "jobs":
                    jobs_by_date.get(
                        calendar_date.isoformat(),
                        []
                    ),
            }

            for calendar_date in week
        ]

        for week in raw_weeks
    ]


# ==========================================================
# SCHEDULE CONFLICT CHECK
# ==========================================================

def schedule_conflict(
    job_id: int,
    scheduled_date: str,
    start: str,
    end: str,
    worker: str
):

    if (
        not start
        or not end
    ):

        return None


    return db().execute(
        """
        SELECT
            job_number,
            job_title,
            start_time,
            end_time,
            assigned_to

        FROM jobs

        WHERE id <> ?

        AND scheduled_date = ?

        AND status NOT IN (
            'Completed',
            'Cancelled'
        )

        AND start_time <> ''

        AND end_time <> ''

        AND start_time < ?

        AND end_time > ?

        AND (
            ? = ''
            OR assigned_to = ''
            OR LOWER(assigned_to)
                = LOWER(?)
        )

        LIMIT 1
        """,
        (
            job_id,
            scheduled_date,
            end,
            start,
            worker,
            worker
        )
    ).fetchone()


# ==========================================================
# ADMIN JOB SCHEDULING PAGE
# ==========================================================

@app.route("/job-scheduling")
@login_required
def job_scheduling():

    today = date.today()


    selected_month = request.args.get(
        "month",
        today.month,
        type=int
    ) or today.month


    selected_year = request.args.get(
        "year",
        today.year,
        type=int
    ) or today.year


    if not 1 <= selected_month <= 12:

        selected_month = today.month


    if not 2000 <= selected_year <= 2100:

        selected_year = today.year


    month_start = date(
        selected_year,
        selected_month,
        1
    )


    previous_month_date = (
        month_start
        - timedelta(
            days=1
        )
    )


    next_month_date = (
        month_start.replace(
            day=28
        )
        + timedelta(
            days=4
        )
    ).replace(
        day=1
    )


    # ------------------------------------------------------
    # PENDING CUSTOMER REQUESTS
    # ------------------------------------------------------

    pending_requests = db().execute(
        """
        SELECT *
        FROM job_requests

        WHERE status = 'Pending'

        ORDER BY

            CASE priority

                WHEN 'Urgent'
                    THEN 1

                WHEN 'High'
                    THEN 2

                WHEN 'Normal'
                    THEN 3

                ELSE 4

            END,

            created_at ASC
        """
    ).fetchall()


    # ------------------------------------------------------
    # ACCEPTED BUT NOT SCHEDULED
    # ------------------------------------------------------

    accepted_unscheduled = db().execute(
        """
        SELECT *
        FROM jobs

        WHERE scheduled_date = ''

        AND status IN (
            'Received',
            'Accepted'
        )

        ORDER BY

            CASE priority

                WHEN 'Urgent'
                    THEN 1

                WHEN 'High'
                    THEN 2

                WHEN 'Normal'
                    THEN 3

                ELSE 4

            END,

            created_at ASC
        """
    ).fetchall()


    # ------------------------------------------------------
    # ALL JOBS
    # ------------------------------------------------------

    jobs = db().execute(
        """
        SELECT *
        FROM jobs

        ORDER BY
            updated_at DESC,
            id DESC

        LIMIT 100
        """
    ).fetchall()


    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    summary = db().execute(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM job_requests
                WHERE status = 'Pending'
            )
            AS pending_requests,


            (
                SELECT COUNT(*)
                FROM jobs

                WHERE scheduled_date = ''

                AND status IN (
                    'Received',
                    'Accepted'
                )
            )
            AS awaiting_schedule,


            (
                SELECT COUNT(*)
                FROM jobs
                WHERE status = 'Scheduled'
            )
            AS scheduled_jobs,


            (
                SELECT COUNT(*)
                FROM jobs
                WHERE status = 'In Progress'
            )
            AS in_progress_jobs,


            (
                SELECT COUNT(*)
                FROM jobs

                WHERE scheduled_date = ?

                AND status NOT IN (
                    'Completed',
                    'Cancelled'
                )
            )
            AS jobs_today,


            (
                SELECT COUNT(*)
                FROM jobs
                WHERE status = 'Completed'
            )
            AS completed_jobs
        """,
        (
            today.isoformat(),
        )
    ).fetchone()


    return render_template(
        "job_scheduling.html",

        calendar_weeks=calendar_weeks(
            selected_year,
            selected_month
        ),

        pending_requests=pending_requests,

        accepted_unscheduled=
            accepted_unscheduled,

        jobs=jobs,

        summary=summary,

        month_name=
            calendar.month_name[
                selected_month
            ],

        selected_month=
            selected_month,

        selected_year=
            selected_year,

        previous_month=
            previous_month_date.month,

        previous_year=
            previous_month_date.year,

        next_month=
            next_month_date.month,

        next_year=
            next_month_date.year,

        today=today,

        today_iso=
            today.isoformat(),

        job_statuses=
            JOB_STATUSES,
    )


# ==========================================================
# ACCEPT CUSTOMER REQUEST
# ==========================================================

@app.route(
    "/job-scheduling/requests/<int:request_id>/accept",
    methods=["POST"]
)
@login_required
def accept_job_request(
    request_id
):

    validate_csrf()


    request_row = request_or_404(
        request_id
    )


    if request_row[
        "status"
    ] != "Pending":

        flash(
            (
                "That request has already "
                "been processed."
            ),
            "error"
        )

        return redirect(
            url_for("job_scheduling")
        )


    job_number = unique_number(
        "JOB",
        "jobs",
        "job_number"
    )


    timestamp = now()


    cursor = db().execute(
        """
        INSERT INTO jobs (
            job_number,
            request_id,
            customer_name,
            customer_phone,
            customer_email,
            job_title,
            job_type,
            description,
            site_address,
            suburb,
            priority,
            status,
            received_date,
            scheduled_date,
            start_time,
            end_time,
            estimated_hours,
            assigned_to,
            notes,
            google_event_id,
            google_sync_status,
            accepted_at,
            completed_at,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?
        )
        """,
        (
            job_number,

            request_id,

            request_row[
                "customer_name"
            ],

            request_row[
                "customer_phone"
            ],

            request_row[
                "customer_email"
            ],

            request_row[
                "job_title"
            ],

            request_row[
                "job_type"
            ],

            request_row[
                "description"
            ],

            request_row[
                "site_address"
            ],

            request_row[
                "suburb"
            ],

            request_row[
                "priority"
            ],

            "Accepted",

            request_row[
                "created_at"
            ][:10],

            "",

            "",

            "",

            0,

            "",

            request_row[
                "notes"
            ],

            "",

            "Not connected",

            timestamp,

            "",

            timestamp,

            timestamp
        )
    )


    db().execute(
        """
        UPDATE job_requests

        SET
            status = 'Accepted',
            job_id = ?,
            decision_at = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            cursor.lastrowid,
            timestamp,
            timestamp,
            request_id
        )
    )


    db().commit()


    flash(
        (
            f'{request_row["request_number"]} '
            f"was accepted as {job_number}. "
            "It is ready to schedule."
        ),
        "success"
    )


    return redirect(
        url_for("job_scheduling")
    )


# ==========================================================
# DECLINE CUSTOMER REQUEST
# ==========================================================

@app.route(
    "/job-scheduling/requests/<int:request_id>/decline",
    methods=["POST"]
)
@login_required
def decline_job_request(
    request_id
):

    validate_csrf()


    request_row = request_or_404(
        request_id
    )


    if request_row[
        "status"
    ] != "Pending":

        flash(
            (
                "That request has already "
                "been processed."
            ),
            "error"
        )

        return redirect(
            url_for("job_scheduling")
        )


    reason = request.form.get(
        "decline_reason",
        ""
    ).strip()[:500]


    timestamp = now()


    db().execute(
        """
        UPDATE job_requests

        SET
            status = 'Declined',
            admin_note = ?,
            decision_at = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            reason,
            timestamp,
            timestamp,
            request_id
        )
    )


    db().commit()


    flash(
        (
            f'{request_row["request_number"]} '
            "was declined."
        ),
        "success"
    )


    return redirect(
        url_for("job_scheduling")
    )


# ==========================================================
# SCHEDULE / RESCHEDULE JOB
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/schedule",
    methods=["POST"]
)
@login_required
def schedule_job(
    job_id
):

    validate_csrf()


    job = job_or_404(
        job_id
    )


    scheduled_date = request.form.get(
        "scheduled_date",
        ""
    ).strip()


    start = request.form.get(
        "start_time",
        ""
    ).strip()


    end = request.form.get(
        "end_time",
        ""
    ).strip()


    worker = request.form.get(
        "assigned_to",
        ""
    ).strip()[:100]


    schedule_notes = request.form.get(
        "schedule_notes",
        ""
    ).strip()[:700]


    errors = []


    if not valid_date(
        scheduled_date
    ):

        errors.append(
            "Enter a valid scheduled date."
        )


    if bool(start) != bool(end):

        errors.append(
            (
                "Enter both a start time and "
                "end time."
            )
        )


    if start:

        if (
            not valid_time(start)

            or not valid_time(end)

            or end <= start
        ):

            errors.append(
                (
                    "Enter a valid time range "
                    "with the end later than "
                    "the start."
                )
            )


    try:

        estimated_hours = round(
            float(
                request.form.get(
                    "estimated_hours",
                    "0"
                )
                or 0
            ),
            2
        )


    except ValueError:

        estimated_hours = 0

        errors.append(
            (
                "Estimated hours must "
                "be a valid number."
            )
        )


    if not 0 <= estimated_hours <= 1000:

        errors.append(
            (
                "Estimated hours must "
                "be between 0 and 1000."
            )
        )


    if (
        not errors
        and start
    ):

        conflict = schedule_conflict(
            job_id,
            scheduled_date,
            start,
            end,
            worker
        )


        if conflict:

            errors.append(
                (
                    "Schedule conflict with "
                    f'{conflict["job_number"]} — '
                    f'{conflict["job_title"]} '
                    f'({conflict["start_time"]}'
                    f'–{conflict["end_time"]}).'
                )
            )


    if errors:

        for message in errors:

            flash(
                message,
                "error"
            )


        return redirect(
            url_for("job_scheduling")
        )


    if job[
        "status"
    ] in {
        "Received",
        "Accepted",
        "Scheduled"
    }:

        next_status = "Scheduled"

    else:

        next_status = job[
            "status"
        ]


    db().execute(
        """
        UPDATE jobs

        SET
            scheduled_date = ?,
            start_time = ?,
            end_time = ?,
            estimated_hours = ?,
            assigned_to = ?,

            notes =
                CASE
                    WHEN ? = ''
                        THEN notes
                    ELSE ?
                END,

            status = ?,

            google_sync_status =
                'Not connected',

            updated_at = ?

        WHERE id = ?
        """,
        (
            scheduled_date,
            start,
            end,
            estimated_hours,
            worker,
            schedule_notes,
            schedule_notes,
            next_status,
            now(),
            job_id
        )
    )


    db().commit()


    # ======================================================
    # FUTURE GOOGLE CALENDAR API INTEGRATION
    # ======================================================
    #
    # When Google Calendar is added later:
    #
    # 1. Build a Google Calendar event from this job.
    #
    # 2. If job["google_event_id"] is empty:
    #       create a new Google event.
    #
    # 3. Otherwise:
    #       update the existing event.
    #
    # 4. Save Google's event ID into:
    #       jobs.google_event_id
    #
    # 5. Set:
    #       jobs.google_sync_status = 'Synced'
    #
    # The TimberOps calendar works independently until then.
    # ======================================================


    flash(
        (
            f'{job["job_number"]} '
            f"was scheduled for "
            f"{scheduled_date}."
        ),
        "success"
    )


    return redirect(
        url_for(
            "job_scheduling",

            month=int(
                scheduled_date[
                    5:7
                ]
            ),

            year=int(
                scheduled_date[
                    :4
                ]
            )
        )
    )


# ==========================================================
# UPDATE JOB STATUS
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/status",
    methods=["POST"]
)
@login_required
def update_job_status(
    job_id
):

    validate_csrf()


    job = job_or_404(
        job_id
    )


    status = request.form.get(
        "status",
        ""
    ).strip()


    if status not in JOB_STATUSES:

        flash(
            "Select a valid job status.",
            "error"
        )

        return redirect(
            url_for("job_scheduling")
        )


    if (
        status in {
            "Scheduled",
            "In Progress",
            "On Hold",
            "Completed"
        }

        and not job[
            "scheduled_date"
        ]
    ):

        flash(
            (
                "Schedule the job before "
                "changing it to that status."
            ),
            "error"
        )

        return redirect(
            url_for("job_scheduling")
        )


    if status == "Completed":

        completed_at = now()

    else:

        completed_at = job[
            "completed_at"
        ]


    db().execute(
        """
        UPDATE jobs

        SET
            status = ?,
            completed_at = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            status,
            completed_at,
            now(),
            job_id
        )
    )


    # ------------------------------------------------------
    # KEEP CUSTOMER-FACING REQUEST STATUS IN SYNC
    # ------------------------------------------------------

    if job[
        "request_id"
    ]:

        if status == "Completed":

            request_status = "Completed"


        elif status == "Cancelled":

            request_status = "Cancelled"


        else:

            request_status = "Accepted"


        db().execute(
            """
            UPDATE job_requests

            SET
                status = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                request_status,
                now(),
                job["request_id"]
            )
        )


    db().commit()


    flash(
        (
            f'{job["job_number"]} '
            f"is now {status}."
        ),
        "success"
    )


    return redirect(
        url_for("job_scheduling")
    )


# ==========================================================
# INITIALISE DATABASE
# ==========================================================

with app.app_context():

    init_db()


# ==========================================================
# START APPLICATION
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )