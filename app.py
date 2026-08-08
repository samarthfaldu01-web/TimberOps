import csv
import io
import json
import os
import re
import sqlite3

import calendar as calendar_module

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for
)


# ==========================================================
# APPLICATION CONFIGURATION
# ==========================================================

BASE_DIRECTORY = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIRECTORY / "timberops.db"


app = Flask(__name__)


# Use an environment variable when the application is deployed.
app.secret_key = os.environ.get(
    "TIMBEROPS_SECRET_KEY",
    "TimberOps2026"
)


# ==========================================================
# STOCK OPTIONS
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
    "Safety Equipment"
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
    "kilograms"
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
        "item_code COLLATE NOCASE ASC"
}


# ==========================================================
# SUPPLIER SEARCH OPTIONS
# ==========================================================

SUPPLIER_SEARCH_TERMS = {
    "Structural Timber":
        "structural timber merchant",

    "Dressed Timber":
        "dressed timber hardwood supplier",

    "Decking Timber":
        "decking timber supplier",

    "Sheet Materials":
        "plywood MDF sheet material supplier",

    "Hardware and Fixings":
        "carpentry hardware and fixings supplier",

    "Adhesives":
        "woodworking adhesive supplier",

    "Finishes and Coatings":
        "wood finishes and coatings supplier",

    "Abrasives":
        "woodworking abrasives supplier",

    "Hand Tools":
        "carpentry hand tools supplier",

    "Power Tools":
        "power tools supplier",

    "Tool Accessories":
        "power tool accessories supplier",

    "Safety Equipment":
        "workplace safety equipment supplier"
}


# Approximate Greater Melbourne rectangular boundary.
MELBOURNE_RECTANGLE = {
    "low": {
        "latitude": -38.55,
        "longitude": 144.35
    },

    "high": {
        "latitude": -37.35,
        "longitude": 145.60
    }
}


# ==========================================================
# DATABASE FUNCTIONS
# ==========================================================

def get_database():
    """
    Returns one SQLite connection for the current request.
    """

    if "database" not in g:

        g.database = sqlite3.connect(
            DATABASE_PATH
        )

        g.database.row_factory = sqlite3.Row

        g.database.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.database


@app.teardown_appcontext
def close_database(_error):
    """
    Closes the database connection after each request.
    """

    database = g.pop(
        "database",
        None
    )

    if database is not None:
        database.close()


def initialise_database():
    """
    Creates the tables and upgrades an older stock table.
    """

    database = get_database()

    schema_path = (
        BASE_DIRECTORY
        / "database.sql"
    )

    with schema_path.open(
        "r",
        encoding="utf-8"
    ) as schema_file:

        database.executescript(
            schema_file.read()
        )

    # Supports older versions of the TimberOps database.
    existing_columns = {
        row["name"]

        for row in database.execute(
            "PRAGMA table_info(stock_items)"
        ).fetchall()
    }

    if "specification" not in existing_columns:

        database.execute(
            """
            ALTER TABLE stock_items
            ADD COLUMN specification
            TEXT NOT NULL DEFAULT ''
            """
        )

    if "unit_cost" not in existing_columns:

        database.execute(
            """
            ALTER TABLE stock_items
            ADD COLUMN unit_cost
            REAL NOT NULL DEFAULT 0
            """
        )

    database.commit()


def current_time():
    """
    Returns the current date and time for SQLite.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ==========================================================
# LOGIN PROTECTION
# ==========================================================

def login_required(route_function):
    """
    Prevents access to protected pages before login.
    """

    @wraps(route_function)
    def protected_route(*args, **kwargs):

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

        return route_function(
            *args,
            **kwargs
        )

    return protected_route


# ==========================================================
# STOCK HELPERS
# ==========================================================

def get_stock_item(item_id):
    """
    Retrieves one stock item.
    """

    return get_database().execute(
        """
        SELECT *
        FROM stock_items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()


def validate_stock_form(form):
    """
    Validates Add Stock and Edit Stock forms.
    """

    errors = []

    stock_data = {
        "item_code": form.get(
            "item_code",
            ""
        ).strip().upper(),

        "item_name": form.get(
            "item_name",
            ""
        ).strip(),

        "category": form.get(
            "category",
            ""
        ).strip(),

        "specification": form.get(
            "specification",
            ""
        ).strip(),

        "unit": form.get(
            "unit",
            ""
        ).strip(),

        "location": form.get(
            "location",
            ""
        ).strip(),

        "notes": form.get(
            "notes",
            ""
        ).strip()
    }

    try:

        stock_data["quantity"] = int(
            form.get(
                "quantity",
                ""
            )
        )

    except (TypeError, ValueError):

        stock_data["quantity"] = 0

        errors.append(
            "Quantity must be a whole number."
        )

    try:

        stock_data["minimum_level"] = int(
            form.get(
                "minimum_level",
                ""
            )
        )

    except (TypeError, ValueError):

        stock_data["minimum_level"] = 0

        errors.append(
            "Reorder level must be a whole number."
        )

    try:

        stock_data["unit_cost"] = round(
            float(
                form.get(
                    "unit_cost",
                    "0"
                ) or 0
            ),
            2
        )

    except (TypeError, ValueError):

        stock_data["unit_cost"] = 0.0

        errors.append(
            "Unit cost must be a valid number."
        )

    if not re.fullmatch(
        r"[A-Z0-9_-]{2,20}",
        stock_data["item_code"]
    ):

        errors.append(
            "Item code must use 2-20 letters, "
            "numbers, hyphens or underscores."
        )

    if not 2 <= len(
        stock_data["item_name"]
    ) <= 100:

        errors.append(
            "Item name must contain 2-100 characters."
        )

    if stock_data["category"] not in CATEGORIES:

        errors.append(
            "Select a valid category."
        )

    if stock_data["unit"] not in UNITS:

        errors.append(
            "Select a valid measurement unit."
        )

    if stock_data["quantity"] < 0:

        errors.append(
            "Quantity cannot be negative."
        )

    if stock_data["minimum_level"] < 0:

        errors.append(
            "Reorder level cannot be negative."
        )

    if stock_data["unit_cost"] < 0:

        errors.append(
            "Unit cost cannot be negative."
        )

    if len(
        stock_data["specification"]
    ) > 200:

        errors.append(
            "Specification cannot exceed 200 characters."
        )

    if len(
        stock_data["location"]
    ) > 100:

        errors.append(
            "Location cannot exceed 100 characters."
        )

    if len(
        stock_data["notes"]
    ) > 500:

        errors.append(
            "Notes cannot exceed 500 characters."
        )

    return stock_data, errors


def record_stock_activity(
    item_id,
    movement_type,
    amount,
    previous_quantity,
    new_quantity,
    reason
):
    """
    Records a stock quantity change.
    """

    get_database().execute(
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
            current_time()
        )
    )


# ==========================================================
# SEARCH AND FILTER HELPERS
# ==========================================================

def build_stock_filters(arguments):
    """
    Creates safe SQL search and sorting sections.
    """

    search_text = arguments.get(
        "search",
        ""
    ).strip()

    selected_category = arguments.get(
        "category",
        ""
    ).strip()

    selected_status = arguments.get(
        "status",
        ""
    ).strip()

    selected_sort = arguments.get(
        "sort",
        "updated_desc"
    ).strip()

    conditions = []
    parameters = []

    if search_text:

        search_value = (
            "%"
            + search_text.lower()
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

        parameters.extend(
            [search_value] * 6
        )

    if selected_category in CATEGORIES:

        conditions.append(
            "category = ?"
        )

        parameters.append(
            selected_category
        )

    if selected_status == "available":

        conditions.append(
            "quantity > minimum_level"
        )

    elif selected_status == "low":

        conditions.append(
            """
            quantity > 0
            AND quantity <= minimum_level
            """
        )

    elif selected_status == "out":

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

    order_section = SORT_OPTIONS.get(
        selected_sort,
        SORT_OPTIONS["updated_desc"]
    )

    return {
        "search": search_text,
        "category": selected_category,
        "status": selected_status,
        "sort": selected_sort,
        "where_section": where_section,
        "parameters": parameters,
        "order_section": order_section
    }


# ==========================================================
# GOOGLE PLACES SUPPLIER SEARCH
# ==========================================================

def search_google_suppliers(
    stock_item,
    suburb
):
    """
    Searches Google Places for possible Melbourne suppliers.
    """

    api_key = os.environ.get(
        "GOOGLE_PLACES_API_KEY",
        ""
    ).strip()

    if not api_key:

        return [], (
            "Google Places API is not configured. "
            "Set GOOGLE_PLACES_API_KEY before starting Flask."
        )

    supplier_term = SUPPLIER_SEARCH_TERMS.get(
        stock_item["category"],
        "carpentry and building materials supplier"
    )

    item_description = (
        f'{stock_item["item_name"]} '
        f'{stock_item["specification"]}'
    ).strip()[:160]

    text_query = (
        f"{supplier_term} for {item_description} "
        f"near {suburb}, Victoria, Australia"
    )

    request_body = {
        "textQuery": text_query,

        "pageSize": 8,

        "languageCode": "en",

        "regionCode": "AU",

        "locationRestriction": {
            "rectangle":
                MELBOURNE_RECTANGLE
        }
    }

    google_request = urllib_request.Request(
        url=(
            "https://places.googleapis.com/"
            "v1/places:searchText"
        ),

        data=json.dumps(
            request_body
        ).encode(
            "utf-8"
        ),

        headers={
            "Content-Type":
                "application/json",

            "X-Goog-Api-Key":
                api_key,

            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.formattedAddress,"
                "places.googleMapsUri,"
                "places.businessStatus,"
                "places.primaryTypeDisplayName"
            )
        },

        method="POST"
    )

    try:

        with urllib_request.urlopen(
            google_request,
            timeout=12
        ) as response:

            response_data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib_error.HTTPError as error:

        error_information = error.read().decode(
            "utf-8",
            errors="replace"
        )

        app.logger.error(
            "Google Places API error: %s",
            error_information
        )

        return [], (
            "Google rejected the supplier search. "
            "Check the API key, billing and Places API access."
        )

    except urllib_error.URLError:

        return [], (
            "The Google supplier service could not be reached."
        )

    except json.JSONDecodeError:

        return [], (
            "Google returned invalid supplier information."
        )

    suppliers = []

    for place in response_data.get(
        "places",
        []
    ):

        business_status = place.get(
            "businessStatus",
            "UNKNOWN"
        )

        if business_status == "CLOSED_PERMANENTLY":
            continue

        suppliers.append(
            {
                "name": place.get(
                    "displayName",
                    {}
                ).get(
                    "text",
                    "Unnamed supplier"
                ),

                "address": place.get(
                    "formattedAddress",
                    "Address unavailable"
                ),

                "maps_url": place.get(
                    "googleMapsUri",
                    ""
                ),

                "status":
                    business_status,

                "type": place.get(
                    "primaryTypeDisplayName",
                    {}
                ).get(
                    "text",
                    "Supplier"
                )
            }
        )

    return suppliers, None


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

        login_is_correct = (
            username == "admin@timberops.com"
            and password == "TimberOps2026"
        )

        if login_is_correct:

            session.clear()

            session[
                "admin_logged_in"
            ] = True

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
# HOMEPAGE
# ==========================================================

@app.route("/home")
@login_required
def home():

    return render_template(
        "homepage.html"
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
# STOCK TRACKER PAGE
# ==========================================================

@app.route("/stock-tracker")
@login_required
def stock_tracker():

    database = get_database()

    filters = build_stock_filters(
        request.args
    )

    page = request.args.get(
        "page",
        1,
        type=int
    )

    if page is None or page < 1:
        page = 1

    records_per_page = 10

    total_records = database.execute(
        f"""
        SELECT COUNT(*)
        FROM stock_items
        {filters["where_section"]}
        """,
        filters["parameters"]
    ).fetchone()[0]

    total_pages = max(
        (
            total_records
            + records_per_page
            - 1
        )
        // records_per_page,
        1
    )

    page = min(
        page,
        total_pages
    )

    stock_items = database.execute(
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

            records_per_page,

            (
                page - 1
            ) * records_per_page
        ]
    ).fetchall()

    summary = database.execute(
        """
        SELECT
            COUNT(*) AS total_items,

            COALESCE(
                SUM(quantity),
                0
            ) AS total_quantity,

            COALESCE(
                SUM(quantity * unit_cost),
                0
            ) AS total_value,

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
            ) AS low_items,

            COALESCE(
                SUM(
                    CASE
                        WHEN quantity = 0
                            THEN 1

                        ELSE 0
                    END
                ),
                0
            ) AS out_items

        FROM stock_items
        """
    ).fetchone()

    activity = database.execute(
        """
        SELECT
            stock_activity.*,
            stock_items.item_name,
            stock_items.unit

        FROM stock_activity

        JOIN stock_items
            ON stock_items.id
            = stock_activity.stock_item_id

        ORDER BY stock_activity.id DESC

        LIMIT 12
        """
    ).fetchall()

    all_stock_items = database.execute(
        """
        SELECT
            id,
            item_name,
            specification

        FROM stock_items

        ORDER BY item_name COLLATE NOCASE
        """
    ).fetchall()

    # ------------------------------------------------------
    # ADD, EDIT AND ADJUST PANELS
    # ------------------------------------------------------

    show_add_form = (
        request.args.get(
            "panel"
        )
        == "add"
    )

    edit_item = None
    adjust_item = None

    edit_item_id = request.args.get(
        "edit",
        type=int
    )

    adjust_item_id = request.args.get(
        "adjust",
        type=int
    )

    if edit_item_id:

        edit_item = get_stock_item(
            edit_item_id
        )

    if adjust_item_id:

        adjust_item = get_stock_item(
            adjust_item_id
        )

    # ------------------------------------------------------
    # SUPPLIER SEARCH
    # ------------------------------------------------------

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

        if supplier_item is None:

            supplier_error = (
                "The selected stock item no longer exists."
            )

        else:

            suppliers, supplier_error = (
                search_google_suppliers(
                    supplier_item,
                    supplier_suburb
                    or "Melbourne VIC"
                )
            )

    return render_template(
        "stock_tracker.html",

        items=stock_items,
        all_items=all_stock_items,
        activity=activity,
        summary=summary,

        categories=CATEGORIES,
        units=UNITS,

        filters=filters,

        page=page,
        total_pages=total_pages,
        total=total_records,

        show_add=show_add_form,
        edit_item=edit_item,
        adjust_item=adjust_item,

        suppliers=suppliers,
        supplier_error=supplier_error,

        supplier_item_id=supplier_item_id,
        supplier_suburb=supplier_suburb
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

    stock_data, errors = validate_stock_form(
        request.form
    )

    if errors:

        for error_message in errors:

            flash(
                error_message,
                "error"
            )

        return redirect(
            url_for(
                "stock_tracker",
                panel="add"
            )
            + "#stock-form-panel"
        )

    database = get_database()

    timestamp = current_time()

    try:

        cursor = database.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stock_data["item_code"],
                stock_data["item_name"],
                stock_data["category"],
                stock_data["specification"],
                stock_data["quantity"],
                stock_data["minimum_level"],
                stock_data["unit"],
                stock_data["location"],
                stock_data["unit_cost"],
                stock_data["notes"],
                timestamp,
                timestamp
            )
        )

        if stock_data["quantity"] > 0:

            record_stock_activity(
                cursor.lastrowid,
                "Initial Stock",
                stock_data["quantity"],
                0,
                stock_data["quantity"],
                "Opening quantity"
            )

        database.commit()

    except sqlite3.IntegrityError:

        database.rollback()

        flash(
            "That item code already exists.",
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                panel="add"
            )
            + "#stock-form-panel"
        )

    flash(
        (
            f'{stock_data["item_name"]} '
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
def edit_stock(item_id):

    current_item = get_stock_item(
        item_id
    )

    if current_item is None:

        flash(
            "Stock item not found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    stock_data, errors = validate_stock_form(
        request.form
    )

    if errors:

        for error_message in errors:

            flash(
                error_message,
                "error"
            )

        return redirect(
            url_for(
                "stock_tracker",
                edit=item_id
            )
            + "#stock-form-panel"
        )

    database = get_database()

    try:

        database.execute(
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
                stock_data["item_code"],
                stock_data["item_name"],
                stock_data["category"],
                stock_data["specification"],
                stock_data["quantity"],
                stock_data["minimum_level"],
                stock_data["unit"],
                stock_data["location"],
                stock_data["unit_cost"],
                stock_data["notes"],
                current_time(),
                item_id
            )
        )

        previous_quantity = current_item[
            "quantity"
        ]

        new_quantity = stock_data[
            "quantity"
        ]

        if previous_quantity != new_quantity:

            record_stock_activity(
                item_id,
                "Edited Quantity",
                abs(
                    new_quantity
                    - previous_quantity
                ),
                previous_quantity,
                new_quantity,
                "Quantity changed in Edit Item"
            )

        database.commit()

    except sqlite3.IntegrityError:

        database.rollback()

        flash(
            "That item code is already being used.",
            "error"
        )

        return redirect(
            url_for(
                "stock_tracker",
                edit=item_id
            )
            + "#stock-form-panel"
        )

    flash(
        (
            f'{stock_data["item_name"]} '
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
def adjust_stock(item_id):

    stock_item = get_stock_item(
        item_id
    )

    if stock_item is None:

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

    except (TypeError, ValueError):

        amount = 0

    if (
        movement not in {"in", "out"}
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
            + "#stock-form-panel"
        )

    previous_quantity = stock_item[
        "quantity"
    ]

    if movement == "in":

        new_quantity = (
            previous_quantity
            + amount
        )

        movement_name = "Stock In"

    else:

        new_quantity = (
            previous_quantity
            - amount
        )

        movement_name = "Stock Out"

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
            + "#stock-form-panel"
        )

    database = get_database()

    database.execute(
        """
        UPDATE stock_items

        SET
            quantity = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            new_quantity,
            current_time(),
            item_id
        )
    )

    record_stock_activity(
        item_id,
        movement_name,
        amount,
        previous_quantity,
        new_quantity,
        reason
    )

    database.commit()

    flash(
        (
            f"{movement_name} saved for "
            f'{stock_item["item_name"]}.'
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
def delete_stock(item_id):

    stock_item = get_stock_item(
        item_id
    )

    if stock_item is None:

        flash(
            "Stock item not found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    database = get_database()

    database.execute(
        """
        DELETE FROM stock_items
        WHERE id = ?
        """,
        (item_id,)
    )

    database.commit()

    flash(
        (
            f'{stock_item["item_name"]} '
            "was deleted."
        ),
        "success"
    )

    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# CSV EXPORT
# ==========================================================

@app.route("/stock-tracker/export.csv")
@login_required
def export_csv():

    filters = build_stock_filters(
        request.args
    )

    stock_rows = get_database().execute(
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

    csv_writer = csv.writer(
        output
    )

    csv_writer.writerow(
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
            "Updated"
        ]
    )

    for stock_row in stock_rows:

        csv_writer.writerow(
            list(stock_row)
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
# APPLICATION STARTUP
# ==========================================================

with app.app_context():

    initialise_database()


    # ==========================================================
# JOB SCHEDULING OPTIONS
# ==========================================================

JOB_STATUSES = (
    "Received",
    "Scheduled",
    "In Progress",
    "Completed",
    "Cancelled",
)


JOB_PRIORITIES = (
    "Low",
    "Normal",
    "High",
    "Urgent",
)


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


# ==========================================================
# JOB SCHEDULING HELPERS
# ==========================================================

def get_job_or_404(job_id: int) -> sqlite3.Row:
    """
    Returns one job record or displays a 404 error.
    """

    job = get_db().execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    if job is None:
        abort(
            404,
            description="The selected job does not exist.",
        )

    return job


def valid_date_text(value: str) -> bool:
    """
    Checks that a string uses the YYYY-MM-DD date format.
    """

    try:
        datetime.strptime(
            value,
            "%Y-%m-%d",
        )

        return True

    except ValueError:
        return False


def valid_time_text(value: str) -> bool:
    """
    Checks that a string uses the HH:MM time format.
    """

    try:
        datetime.strptime(
            value,
            "%H:%M",
        )

        return True

    except ValueError:
        return False


def validate_job_form(
    form: Any,
) -> tuple[dict[str, Any], list[str]]:
    """
    Validates information submitted through the Add Job
    and Edit Job forms.
    """

    errors: list[str] = []

    job_number = form.get(
        "job_number",
        "",
    ).strip().upper()

    customer_name = form.get(
        "customer_name",
        "",
    ).strip()

    customer_phone = form.get(
        "customer_phone",
        "",
    ).strip()

    customer_email = form.get(
        "customer_email",
        "",
    ).strip()

    job_title = form.get(
        "job_title",
        "",
    ).strip()

    job_type = form.get(
        "job_type",
        "",
    ).strip()

    description = form.get(
        "description",
        "",
    ).strip()

    site_address = form.get(
        "site_address",
        "",
    ).strip()

    suburb = form.get(
        "suburb",
        "",
    ).strip()

    priority = form.get(
        "priority",
        "Normal",
    ).strip()

    status = form.get(
        "status",
        "Received",
    ).strip()

    received_date = form.get(
        "received_date",
        "",
    ).strip()

    scheduled_date = form.get(
        "scheduled_date",
        "",
    ).strip()

    start_time = form.get(
        "start_time",
        "",
    ).strip()

    end_time = form.get(
        "end_time",
        "",
    ).strip()

    assigned_to = form.get(
        "assigned_to",
        "",
    ).strip()

    notes = form.get(
        "notes",
        "",
    ).strip()

    try:
        estimated_hours = round(
            float(
                form.get(
                    "estimated_hours",
                    "0",
                )
                or 0
            ),
            2,
        )

    except (TypeError, ValueError):
        estimated_hours = 0

        errors.append(
            "Estimated hours must be a valid number.",
        )

    if not re.fullmatch(
        r"[A-Z0-9_-]{2,20}",
        job_number,
    ):
        errors.append(
            "Job number must be 2-20 characters using "
            "letters, numbers, hyphens or underscores.",
        )

    if not 2 <= len(customer_name) <= 100:
        errors.append(
            "Customer name must contain 2-100 characters.",
        )

    if not 2 <= len(job_title) <= 120:
        errors.append(
            "Job title must contain 2-120 characters.",
        )

    if job_type not in JOB_TYPES:
        errors.append(
            "Select a valid job type.",
        )

    if priority not in JOB_PRIORITIES:
        errors.append(
            "Select a valid job priority.",
        )

    if status not in JOB_STATUSES:
        errors.append(
            "Select a valid job status.",
        )

    if not received_date or not valid_date_text(
        received_date,
    ):
        errors.append(
            "Enter a valid received date.",
        )

    if scheduled_date and not valid_date_text(
        scheduled_date,
    ):
        errors.append(
            "Enter a valid scheduled date.",
        )

    if bool(start_time) != bool(end_time):
        errors.append(
            "Enter both a start time and an end time.",
        )

    if start_time and not valid_time_text(
        start_time,
    ):
        errors.append(
            "Enter a valid start time.",
        )

    if end_time and not valid_time_text(
        end_time,
    ):
        errors.append(
            "Enter a valid end time.",
        )

    if (
        start_time
        and end_time
        and valid_time_text(start_time)
        and valid_time_text(end_time)
        and end_time <= start_time
    ):
        errors.append(
            "The end time must be later than the start time.",
        )

    statuses_requiring_schedule = {
        "Scheduled",
        "In Progress",
        "Completed",
    }

    if (
        status in statuses_requiring_schedule
        and not scheduled_date
    ):
        errors.append(
            f"A scheduled date is required when the status is {status}.",
        )

    # Automatically marks a received job as scheduled when
    # scheduling information has been entered.
    if scheduled_date and status == "Received":
        status = "Scheduled"

    if estimated_hours < 0:
        errors.append(
            "Estimated hours cannot be negative.",
        )

    if estimated_hours > 1000:
        errors.append(
            "Estimated hours is too large.",
        )

    if len(customer_phone) > 30:
        errors.append(
            "Customer phone cannot exceed 30 characters.",
        )

    if len(customer_email) > 120:
        errors.append(
            "Customer email cannot exceed 120 characters.",
        )

    if len(description) > 1000:
        errors.append(
            "Job description cannot exceed 1000 characters.",
        )

    if len(site_address) > 180:
        errors.append(
            "Site address cannot exceed 180 characters.",
        )

    if len(suburb) > 80:
        errors.append(
            "Suburb cannot exceed 80 characters.",
        )

    if len(assigned_to) > 100:
        errors.append(
            "Assigned worker cannot exceed 100 characters.",
        )

    if len(notes) > 700:
        errors.append(
            "Job notes cannot exceed 700 characters.",
        )

    job_data = {
        "job_number": job_number,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "job_title": job_title,
        "job_type": job_type,
        "description": description,
        "site_address": site_address,
        "suburb": suburb,
        "priority": priority,
        "status": status,
        "received_date": received_date,
        "scheduled_date": scheduled_date,
        "start_time": start_time,
        "end_time": end_time,
        "estimated_hours": estimated_hours,
        "assigned_to": assigned_to,
        "notes": notes,
    }

    return job_data, errors


def build_job_filters(
    arguments: Any,
) -> tuple[
    str,
    list[Any],
    str,
    str,
    str,
]:
    """
    Creates a safe SQL filtering section for job records.
    """

    search_text = arguments.get(
        "q",
        "",
    ).strip()

    selected_status = arguments.get(
        "status",
        "",
    ).strip()

    selected_priority = arguments.get(
        "priority",
        "",
    ).strip()

    where_clauses: list[str] = []
    parameters: list[Any] = []

    if search_text:
        search_pattern = (
            "%"
            + search_text.lower()
            + "%"
        )

        where_clauses.append(
            """
            (
                LOWER(job_number) LIKE ?
                OR LOWER(customer_name) LIKE ?
                OR LOWER(job_title) LIKE ?
                OR LOWER(job_type) LIKE ?
                OR LOWER(suburb) LIKE ?
                OR LOWER(assigned_to) LIKE ?
            )
            """
        )

        parameters.extend(
            [search_pattern] * 6,
        )

    if selected_status in JOB_STATUSES:
        where_clauses.append(
            "status = ?",
        )

        parameters.append(
            selected_status,
        )

    if selected_priority in JOB_PRIORITIES:
        where_clauses.append(
            "priority = ?",
        )

        parameters.append(
            selected_priority,
        )

    where_sql = ""

    if where_clauses:
        where_sql = (
            " WHERE "
            + " AND ".join(
                where_clauses,
            )
        )

    return (
        where_sql,
        parameters,
        search_text,
        selected_status,
        selected_priority,
    )


# ==========================================================
# JOB SCHEDULING PAGE
# ==========================================================

@app.route("/job-scheduling")
@login_required
def job_scheduling() -> str:
    """
    Displays the monthly calendar, received-jobs queue,
    upcoming jobs and complete job list.
    """

    database = get_db()

    today = date.today()

    selected_month = request.args.get(
        "month",
        today.month,
        type=int,
    )

    selected_year = request.args.get(
        "year",
        today.year,
        type=int,
    )

    if selected_month not in range(1, 13):
        selected_month = today.month

    if selected_year not in range(2000, 2101):
        selected_year = today.year

    (
        where_sql,
        filter_parameters,
        search_text,
        selected_status,
        selected_priority,
    ) = build_job_filters(
        request.args,
    )

    month_start = date(
        selected_year,
        selected_month,
        1,
    )

    previous_month_date = (
        month_start
        - timedelta(days=1)
    )

    next_month_date = (
        month_start.replace(day=28)
        + timedelta(days=4)
    ).replace(day=1)

    calendar_builder = calendar_module.Calendar(
        firstweekday=0,
    )

    raw_calendar_weeks = calendar_builder.monthdatescalendar(
        selected_year,
        selected_month,
    )

    visible_start = raw_calendar_weeks[0][0]
    visible_end = raw_calendar_weeks[-1][-1]

    calendar_where_clauses: list[str] = [
        "scheduled_date BETWEEN ? AND ?",
    ]

    calendar_parameters: list[Any] = [
        visible_start.isoformat(),
        visible_end.isoformat(),
    ]

    if where_sql:
        filter_condition = where_sql.replace(
            " WHERE ",
            "",
            1,
        )

        calendar_where_clauses.append(
            filter_condition,
        )

        calendar_parameters.extend(
            filter_parameters,
        )

    calendar_jobs = database.execute(
        f"""
        SELECT *
        FROM jobs
        WHERE {" AND ".join(calendar_where_clauses)}
        ORDER BY
            scheduled_date ASC,
            start_time ASC,
            priority DESC,
            id ASC
        """,
        calendar_parameters,
    ).fetchall()

    jobs_by_date: dict[str, list[sqlite3.Row]] = {}

    for job in calendar_jobs:
        scheduled_date = job[
            "scheduled_date"
        ]

        jobs_by_date.setdefault(
            scheduled_date,
            [],
        ).append(
            job,
        )

    calendar_weeks: list[list[dict[str, Any]]] = []

    for week in raw_calendar_weeks:
        calendar_week: list[dict[str, Any]] = []

        for calendar_date in week:
            date_text = calendar_date.isoformat()

            calendar_week.append(
                {
                    "iso": date_text,
                    "day_number": calendar_date.day,
                    "in_month": (
                        calendar_date.month
                        == selected_month
                    ),
                    "is_today": (
                        calendar_date
                        == today
                    ),
                    "jobs": jobs_by_date.get(
                        date_text,
                        [],
                    ),
                },
            )

        calendar_weeks.append(
            calendar_week,
        )

    all_filtered_jobs = database.execute(
        f"""
        SELECT *
        FROM jobs
        {where_sql}
        ORDER BY
            CASE
                WHEN scheduled_date = '' THEN 1
                ELSE 0
            END,
            scheduled_date ASC,
            start_time ASC,
            received_date DESC,
            id DESC
        LIMIT 100
        """,
        filter_parameters,
    ).fetchall()

    summary = database.execute(
        """
        SELECT
            COUNT(*) AS total_jobs,

            SUM(
                CASE
                    WHEN status = 'Received'
                    THEN 1 ELSE 0
                END
            ) AS received_jobs,

            SUM(
                CASE
                    WHEN status = 'Scheduled'
                    THEN 1 ELSE 0
                END
            ) AS scheduled_jobs,

            SUM(
                CASE
                    WHEN status = 'In Progress'
                    THEN 1 ELSE 0
                END
            ) AS in_progress_jobs,

            SUM(
                CASE
                    WHEN status = 'Completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_jobs,

            SUM(
                CASE
                    WHEN scheduled_date = ?
                    AND status NOT IN (
                        'Completed',
                        'Cancelled'
                    )
                    THEN 1 ELSE 0
                END
            ) AS jobs_today

        FROM jobs
        """,
        (
            today.isoformat(),
        ),
    ).fetchone()

    unscheduled_jobs = database.execute(
        """
        SELECT *
        FROM jobs

        WHERE scheduled_date = ''
        AND status NOT IN (
            'Completed',
            'Cancelled'
        )

        ORDER BY
            CASE priority
                WHEN 'Urgent' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Normal' THEN 3
                ELSE 4
            END,
            received_date ASC,
            id ASC

        LIMIT 8
        """
    ).fetchall()

    upcoming_end = (
        today
        + timedelta(days=30)
    ).isoformat()

    upcoming_jobs = database.execute(
        """
        SELECT *
        FROM jobs

        WHERE scheduled_date BETWEEN ? AND ?
        AND status NOT IN (
            'Completed',
            'Cancelled'
        )

        ORDER BY
            scheduled_date ASC,
            start_time ASC

        LIMIT 8
        """,
        (
            today.isoformat(),
            upcoming_end,
        ),
    ).fetchall()

    show_add_form = (
        request.args.get(
            "panel",
            "",
        )
        == "add"
    )

    edit_job_record = None
    schedule_job_record = None

    edit_job_id = request.args.get(
        "edit",
        type=int,
    )

    schedule_job_id = request.args.get(
        "schedule",
        type=int,
    )

    if edit_job_id:
        edit_job_record = get_job_or_404(
            edit_job_id,
        )

    if schedule_job_id:
        schedule_job_record = get_job_or_404(
            schedule_job_id,
        )

    return render_template(
        "job_scheduling.html",

        calendar_weeks=calendar_weeks,
        month_name=calendar_module.month_name[
            selected_month
        ],

        selected_month=selected_month,
        selected_year=selected_year,

        previous_month=previous_month_date.month,
        previous_year=previous_month_date.year,

        next_month=next_month_date.month,
        next_year=next_month_date.year,

        today=today,
        today_iso=today.isoformat(),

        jobs=all_filtered_jobs,
        unscheduled_jobs=unscheduled_jobs,
        upcoming_jobs=upcoming_jobs,
        summary=summary,

        job_statuses=JOB_STATUSES,
        job_priorities=JOB_PRIORITIES,
        job_types=JOB_TYPES,

        search_text=search_text,
        selected_status=selected_status,
        selected_priority=selected_priority,

        show_add_form=show_add_form,
        edit_job=edit_job_record,
        schedule_job=schedule_job_record,
    )


# ==========================================================
# ADD JOB
# ==========================================================

@app.route(
    "/job-scheduling/add",
    methods=["POST"],
)
@login_required
def add_job() -> Response:
    """
    Creates a new received or scheduled job.
    """

    validate_csrf()

    job_data, errors = validate_job_form(
        request.form,
    )

    if errors:
        for error in errors:
            flash(
                error,
                "error",
            )

        return redirect(
            url_for(
                "job_scheduling",
                panel="add",
            )
            + "#job-form-panel"
        )

    database = get_db()
    timestamp = current_time()

    try:
        database.execute(
            """
            INSERT INTO jobs (
                job_number,
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
                job_data["job_number"],
                job_data["customer_name"],
                job_data["customer_phone"],
                job_data["customer_email"],
                job_data["job_title"],
                job_data["job_type"],
                job_data["description"],
                job_data["site_address"],
                job_data["suburb"],
                job_data["priority"],
                job_data["status"],
                job_data["received_date"],
                job_data["scheduled_date"],
                job_data["start_time"],
                job_data["end_time"],
                job_data["estimated_hours"],
                job_data["assigned_to"],
                job_data["notes"],
                timestamp,
                timestamp,
            ),
        )

        database.commit()

    except sqlite3.IntegrityError:
        database.rollback()

        flash(
            "That job number already exists. "
            "Enter a unique job number.",
            "error",
        )

        return redirect(
            url_for(
                "job_scheduling",
                panel="add",
            )
            + "#job-form-panel"
        )

    flash(
        f"Job {job_data['job_number']} was added successfully.",
        "success",
    )

    return redirect(
        url_for("job_scheduling"),
    )


# ==========================================================
# EDIT JOB
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/edit",
    methods=["POST"],
)
@login_required
def edit_job(job_id: int) -> Response:
    """
    Updates an existing job.
    """

    validate_csrf()

    get_job_or_404(
        job_id,
    )

    job_data, errors = validate_job_form(
        request.form,
    )

    if errors:
        for error in errors:
            flash(
                error,
                "error",
            )

        return redirect(
            url_for(
                "job_scheduling",
                edit=job_id,
            )
            + "#job-form-panel"
        )

    database = get_db()

    try:
        database.execute(
            """
            UPDATE jobs

            SET
                job_number = ?,
                customer_name = ?,
                customer_phone = ?,
                customer_email = ?,
                job_title = ?,
                job_type = ?,
                description = ?,
                site_address = ?,
                suburb = ?,
                priority = ?,
                status = ?,
                received_date = ?,
                scheduled_date = ?,
                start_time = ?,
                end_time = ?,
                estimated_hours = ?,
                assigned_to = ?,
                notes = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                job_data["job_number"],
                job_data["customer_name"],
                job_data["customer_phone"],
                job_data["customer_email"],
                job_data["job_title"],
                job_data["job_type"],
                job_data["description"],
                job_data["site_address"],
                job_data["suburb"],
                job_data["priority"],
                job_data["status"],
                job_data["received_date"],
                job_data["scheduled_date"],
                job_data["start_time"],
                job_data["end_time"],
                job_data["estimated_hours"],
                job_data["assigned_to"],
                job_data["notes"],
                current_time(),
                job_id,
            ),
        )

        database.commit()

    except sqlite3.IntegrityError:
        database.rollback()

        flash(
            "That job number is already being used.",
            "error",
        )

        return redirect(
            url_for(
                "job_scheduling",
                edit=job_id,
            )
            + "#job-form-panel"
        )

    flash(
        f"Job {job_data['job_number']} was updated.",
        "success",
    )

    return redirect(
        url_for("job_scheduling"),
    )


# ==========================================================
# SCHEDULE A RECEIVED JOB
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/schedule",
    methods=["POST"],
)
@login_required
def schedule_existing_job(
    job_id: int,
) -> Response:
    """
    Assigns a date, time and worker to a received job.
    """

    validate_csrf()

    job = get_job_or_404(
        job_id,
    )

    scheduled_date = request.form.get(
        "scheduled_date",
        "",
    ).strip()

    start_time = request.form.get(
        "start_time",
        "",
    ).strip()

    end_time = request.form.get(
        "end_time",
        "",
    ).strip()

    assigned_to = request.form.get(
        "assigned_to",
        "",
    ).strip()

    errors: list[str] = []

    if not scheduled_date or not valid_date_text(
        scheduled_date,
    ):
        errors.append(
            "Enter a valid scheduled date.",
        )

    if bool(start_time) != bool(end_time):
        errors.append(
            "Enter both a start time and end time.",
        )

    if start_time and not valid_time_text(
        start_time,
    ):
        errors.append(
            "Enter a valid start time.",
        )

    if end_time and not valid_time_text(
        end_time,
    ):
        errors.append(
            "Enter a valid end time.",
        )

    if (
        start_time
        and end_time
        and valid_time_text(start_time)
        and valid_time_text(end_time)
        and end_time <= start_time
    ):
        errors.append(
            "The end time must be later than the start time.",
        )

    if len(assigned_to) > 100:
        errors.append(
            "Assigned worker cannot exceed 100 characters.",
        )

    if errors:
        for error in errors:
            flash(
                error,
                "error",
            )

        return redirect(
            url_for(
                "job_scheduling",
                schedule=job_id,
            )
            + "#job-form-panel"
        )

    get_db().execute(
        """
        UPDATE jobs

        SET
            scheduled_date = ?,
            start_time = ?,
            end_time = ?,
            assigned_to = ?,
            status = 'Scheduled',
            updated_at = ?

        WHERE id = ?
        """,
        (
            scheduled_date,
            start_time,
            end_time,
            assigned_to,
            current_time(),
            job_id,
        ),
    )

    get_db().commit()

    flash(
        f"{job['job_number']} was added to the schedule.",
        "success",
    )

    return redirect(
        url_for(
            "job_scheduling",
            month=int(
                scheduled_date[5:7]
            ),
            year=int(
                scheduled_date[0:4]
            ),
        ),
    )


# ==========================================================
# UPDATE JOB STATUS
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/status",
    methods=["POST"],
)
@login_required
def update_job_status(
    job_id: int,
) -> Response:
    """
    Changes the progress status of a job.
    """

    validate_csrf()

    job = get_job_or_404(
        job_id,
    )

    new_status = request.form.get(
        "status",
        "",
    ).strip()

    if new_status not in JOB_STATUSES:
        flash(
            "Select a valid job status.",
            "error",
        )

        return redirect(
            url_for("job_scheduling"),
        )

    if (
        new_status in {
            "Scheduled",
            "In Progress",
            "Completed",
        }
        and not job["scheduled_date"]
    ):
        flash(
            "Schedule the job before changing it to this status.",
            "error",
        )

        return redirect(
            url_for(
                "job_scheduling",
                schedule=job_id,
            )
            + "#job-form-panel"
        )

    get_db().execute(
        """
        UPDATE jobs

        SET
            status = ?,
            updated_at = ?

        WHERE id = ?
        """,
        (
            new_status,
            current_time(),
            job_id,
        ),
    )

    get_db().commit()

    flash(
        f"{job['job_number']} is now {new_status}.",
        "success",
    )

    return redirect(
        url_for("job_scheduling"),
    )


# ==========================================================
# DELETE JOB
# ==========================================================

@app.route(
    "/job-scheduling/<int:job_id>/delete",
    methods=["POST"],
)
@login_required
def delete_job(
    job_id: int,
) -> Response:
    """
    Permanently removes a job record.
    """

    validate_csrf()

    job = get_job_or_404(
        job_id,
    )

    get_db().execute(
        """
        DELETE FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    )

    get_db().commit()

    flash(
        f"Job {job['job_number']} was deleted.",
        "success",
    )

    return redirect(
        url_for("job_scheduling"),
    )

# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
    