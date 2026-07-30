import os
import sqlite3

from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for
)


# ==========================================================
# FLASK APPLICATION
# ==========================================================

app = Flask(__name__)

# Used to protect Flask session information.
app.secret_key = "TimberOps2026"


# Absolute path to the project folder.
BASE_DIRECTORY = os.path.abspath(
    os.path.dirname(__file__)
)


# Absolute path to the SQLite database.
DATABASE_PATH = os.path.join(
    BASE_DIRECTORY,
    "timberops.db"
)


# ==========================================================
# DATABASE FUNCTIONS
# ==========================================================

def get_database():
    """
    Opens one SQLite database connection for the current
    request.
    """

    if "database" not in g:

        g.database = sqlite3.connect(
            DATABASE_PATH
        )

        # Allows rows to be accessed using column names.
        g.database.row_factory = sqlite3.Row

        # Enables SQLite foreign-key support.
        g.database.execute(
            "PRAGMA foreign_keys = ON"
        )

    return g.database


@app.teardown_appcontext
def close_database(error):
    """
    Closes the database connection after the request ends.
    """

    database = g.pop(
        "database",
        None
    )

    if database is not None:
        database.close()


def initialise_database():
    """
    Reads database.sql and creates the required database
    tables when they do not already exist.
    """

    database = get_database()

    sql_file_path = os.path.join(
        BASE_DIRECTORY,
        "database.sql"
    )

    with open(
        sql_file_path,
        "r",
        encoding="utf-8"
    ) as sql_file:

        database.executescript(
            sql_file.read()
        )

    database.commit()


def current_time():
    """
    Returns the current date and time in a format suitable
    for SQLite.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ==========================================================
# LOGIN PROTECTION
# ==========================================================

def login_required(route_function):
    """
    Prevents users from accessing protected pages unless
    they have logged in.
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
# GENERAL ROUTES
# ==========================================================

@app.route("/")
def index():
    """
    Sends users to the correct starting page.
    """

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
# ADMIN LOGIN
# ==========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():
    """
    Displays and processes the administrator login page.
    """

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Email and password are required.",
                "error"
            )

            return redirect(
                url_for("admin_login")
            )

        # Temporary administrator login details.
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
            "Invalid email or password. Please try again.",
            "error"
        )

        return redirect(
            url_for("admin_login")
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
    """
    Displays the TimberOps dashboard homepage.
    """

    return render_template(
        "homepage.html"
    )


# ==========================================================
# FORGOT PASSWORD
# ==========================================================

@app.route("/forgot-password")
def forgot_password():
    """
    Displays the forgot-password information page.
    """

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
    """
    Removes the administrator login session.
    """

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ==========================================================
# STOCK TRACKER
# ==========================================================

@app.route("/stock-tracker")
@login_required
def stock_tracker():
    """
    Displays stock records and handles search, category,
    status and sorting filters.
    """

    database = get_database()

    # Retrieves filter information from the page URL.
    search_text = request.args.get(
        "search",
        ""
    ).strip()

    selected_category = request.args.get(
        "category",
        ""
    ).strip()

    selected_status = request.args.get(
        "status",
        ""
    ).strip()

    selected_sort = request.args.get(
        "sort",
        "newest"
    ).strip()

    conditions = []
    parameters = []

    # ------------------------------------------------------
    # SEARCH FILTER
    # ------------------------------------------------------

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
                OR LOWER(location) LIKE ?
                OR LOWER(notes) LIKE ?
            )
            """
        )

        parameters.extend(
            [
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ]
        )

    # ------------------------------------------------------
    # CATEGORY FILTER
    # ------------------------------------------------------

    if selected_category:

        conditions.append(
            "category = ?"
        )

        parameters.append(
            selected_category
        )

    # ------------------------------------------------------
    # STATUS FILTER
    # ------------------------------------------------------

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

    # Creates the SQL WHERE section.
    if conditions:

        where_section = (
            " WHERE "
            + " AND ".join(
                conditions
            )
        )

    else:

        where_section = ""

    # ------------------------------------------------------
    # SORTING
    # ------------------------------------------------------

    allowed_sorting = {
        "newest":
            "updated_at DESC",

        "oldest":
            "updated_at ASC",

        "name_az":
            "item_name COLLATE NOCASE ASC",

        "name_za":
            "item_name COLLATE NOCASE DESC",

        "quantity_low":
            "quantity ASC",

        "quantity_high":
            "quantity DESC",

        "code":
            "item_code COLLATE NOCASE ASC"
    }

    order_section = allowed_sorting.get(
        selected_sort,
        allowed_sorting["newest"]
    )

    # ------------------------------------------------------
    # RETRIEVE STOCK ITEMS
    # ------------------------------------------------------

    stock_query = f"""
        SELECT *
        FROM stock_items

        {where_section}

        ORDER BY {order_section}
    """

    stock_items = database.execute(
        stock_query,
        parameters
    ).fetchall()

    # ------------------------------------------------------
    # CATEGORY OPTIONS
    # ------------------------------------------------------

    categories = database.execute(
        """
        SELECT DISTINCT category
        FROM stock_items
        ORDER BY category COLLATE NOCASE
        """
    ).fetchall()

    # ------------------------------------------------------
    # SUMMARY INFORMATION
    # ------------------------------------------------------

    summary = database.execute(
        """
        SELECT
            COUNT(*) AS total_items,

            COALESCE(
                SUM(quantity),
                0
            ) AS total_quantity,

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
            ) AS low_stock_items,

            COALESCE(
                SUM(
                    CASE
                        WHEN quantity = 0
                        THEN 1

                        ELSE 0
                    END
                ),
                0
            ) AS out_of_stock_items

        FROM stock_items
        """
    ).fetchone()

    # ------------------------------------------------------
    # STOCK HISTORY
    # ------------------------------------------------------

    stock_history = database.execute(
        """
        SELECT
            stock_history.*,
            stock_items.item_code,
            stock_items.item_name,
            stock_items.unit

        FROM stock_history

        JOIN stock_items
            ON stock_items.id
            = stock_history.stock_item_id

        ORDER BY
            stock_history.created_at DESC,
            stock_history.id DESC

        LIMIT 12
        """
    ).fetchall()

    return render_template(
        "stock_tracker.html",

        stock_items=stock_items,
        categories=categories,
        summary=summary,
        stock_history=stock_history,

        search_text=search_text,

        selected_category=selected_category,
        selected_status=selected_status,
        selected_sort=selected_sort
    )


# ==========================================================
# ADD STOCK ITEM
# ==========================================================

@app.route(
    "/stock/add",
    methods=["POST"]
)
@login_required
def add_stock():
    """
    Validates and adds a new stock item.
    """

    item_code = request.form.get(
        "item_code",
        ""
    ).strip().upper()

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    unit = request.form.get(
        "unit",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    quantity_text = request.form.get(
        "quantity",
        ""
    ).strip()

    minimum_text = request.form.get(
        "minimum_level",
        ""
    ).strip()

    # ------------------------------------------------------
    # SERVER-SIDE VALIDATION
    # ------------------------------------------------------

    if (
        not item_code
        or not item_name
        or not category
        or not unit
    ):

        flash(
            "Complete all required stock fields.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    try:

        quantity = int(
            quantity_text
        )

        minimum_level = int(
            minimum_text
        )

    except ValueError:

        flash(
            "Quantity and minimum level must be whole numbers.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if quantity < 0 or minimum_level < 0:

        flash(
            "Stock values cannot be negative.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if len(item_code) > 20:

        flash(
            "Item code cannot exceed 20 characters.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if len(item_name) > 100:

        flash(
            "Item name cannot exceed 100 characters.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
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
                quantity,
                minimum_level,
                unit,
                location,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_code,
                item_name,
                category,
                quantity,
                minimum_level,
                unit,
                location,
                notes,
                timestamp,
                timestamp
            )
        )

        item_id = cursor.lastrowid

        if quantity > 0:

            database.execute(
                """
                INSERT INTO stock_history (
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
                    "Initial Stock",
                    quantity,
                    0,
                    quantity,
                    "Opening quantity",
                    timestamp
                )
            )

        database.commit()

    except sqlite3.IntegrityError:

        database.rollback()

        flash(
            "That item code already exists.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    flash(
        f"{item_name} was added successfully.",
        "success"
    )

    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# EDIT STOCK ITEM
# ==========================================================

@app.route(
    "/stock/<int:item_id>/edit",
    methods=["POST"]
)
@login_required
def edit_stock(item_id):
    """
    Updates an existing stock item.
    """

    database = get_database()

    current_item = database.execute(
        """
        SELECT *
        FROM stock_items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()

    if current_item is None:

        flash(
            "Stock item could not be found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    item_code = request.form.get(
        "item_code",
        ""
    ).strip().upper()

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    unit = request.form.get(
        "unit",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    try:

        quantity = int(
            request.form.get(
                "quantity",
                ""
            )
        )

        minimum_level = int(
            request.form.get(
                "minimum_level",
                ""
            )
        )

    except ValueError:

        flash(
            "Quantity and minimum level must be whole numbers.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if (
        not item_code
        or not item_name
        or not category
        or not unit
    ):

        flash(
            "Complete all required fields.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if quantity < 0 or minimum_level < 0:

        flash(
            "Stock values cannot be negative.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    timestamp = current_time()

    try:

        database.execute(
            """
            UPDATE stock_items

            SET
                item_code = ?,
                item_name = ?,
                category = ?,
                quantity = ?,
                minimum_level = ?,
                unit = ?,
                location = ?,
                notes = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                item_code,
                item_name,
                category,
                quantity,
                minimum_level,
                unit,
                location,
                notes,
                timestamp,
                item_id
            )
        )

        old_quantity = current_item[
            "quantity"
        ]

        if quantity != old_quantity:

            database.execute(
                """
                INSERT INTO stock_history (
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
                    "Edited",
                    abs(
                        quantity
                        - old_quantity
                    ),
                    old_quantity,
                    quantity,
                    "Quantity changed through Edit Stock",
                    timestamp
                )
            )

        database.commit()

    except sqlite3.IntegrityError:

        database.rollback()

        flash(
            "That item code is already being used.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    flash(
        f"{item_name} was updated successfully.",
        "success"
    )

    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# CHECK STOCK IN OR OUT
# ==========================================================

@app.route(
    "/stock/<int:item_id>/adjust",
    methods=["POST"]
)
@login_required
def adjust_stock(item_id):
    """
    Adds or removes a quantity from an existing stock item.
    """

    database = get_database()

    item = database.execute(
        """
        SELECT *
        FROM stock_items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()

    if item is None:

        flash(
            "Stock item could not be found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    adjustment_type = request.form.get(
        "adjustment_type",
        ""
    )

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    try:

        amount = int(
            request.form.get(
                "amount",
                ""
            )
        )

    except ValueError:

        flash(
            "Adjustment amount must be a whole number.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    if amount <= 0:

        flash(
            "Adjustment amount must be greater than zero.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    old_quantity = item[
        "quantity"
    ]

    if adjustment_type == "in":

        new_quantity = (
            old_quantity
            + amount
        )

        movement_type = "Stock In"

    elif adjustment_type == "out":

        new_quantity = (
            old_quantity
            - amount
        )

        movement_type = "Stock Out"

        if new_quantity < 0:

            flash(
                (
                    "You cannot check out more stock "
                    "than is currently available."
                ),
                "error"
            )

            return redirect(
                url_for("stock_tracker")
            )

    else:

        flash(
            "Select Stock In or Stock Out.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

    timestamp = current_time()

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
            timestamp,
            item_id
        )
    )

    database.execute(
        """
        INSERT INTO stock_history (
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
            old_quantity,
            new_quantity,
            reason,
            timestamp
        )
    )

    database.commit()

    flash(
        (
            f"{movement_type} completed for "
            f'{item["item_name"]}.'
        ),
        "success"
    )

    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# DELETE STOCK ITEM
# ==========================================================

@app.route(
    "/stock/<int:item_id>/delete",
    methods=["POST"]
)
@login_required
def delete_stock(item_id):
    """
    Permanently removes a stock item and its history.
    """

    database = get_database()

    item = database.execute(
        """
        SELECT *
        FROM stock_items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()

    if item is None:

        flash(
            "Stock item could not be found.",
            "error"
        )

        return redirect(
            url_for("stock_tracker")
        )

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
            f'{item["item_name"]} '
            "was permanently removed."
        ),
        "success"
    )

    return redirect(
        url_for("stock_tracker")
    )


# ==========================================================
# APPLICATION STARTUP
# ==========================================================

with app.app_context():
    initialise_database()


if __name__ == "__main__":

    app.run(
        debug=True
    )