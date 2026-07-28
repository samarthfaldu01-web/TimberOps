from flask import Flask, render_template, request, redirect, url_for, flash, session


# Creates the Flask application.
app = Flask(__name__)


# Secret key used to protect session and flash-message data.
# In a deployed application, this should be stored in an
# environment variable rather than directly in the source code.
app.secret_key = 'TiberOps2026'


# ----------------------------------------------------------
# Admin Login
# Displays the login form and validates administrator details.
# ----------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    # Process the form only when it has been submitted.
    if request.method == 'POST':

        # Retrieve and clean the submitted login values.
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Server-side validation prevents empty data from being
        # processed even if browser validation is bypassed.
        if not username or not password:
            flash('Email and password are required.')
            return redirect(url_for('admin_login'))

        # Temporary administrator credentials.
        # These should later be replaced by database authentication.
        if (
            username == 'admin@timberops.com'
            and password == 'TimberOps2026'
        ):
            # Records that the administrator has logged in.
            session['admin_logged_in'] = True

            # Redirects to the dashboard homepage.
            return redirect(url_for('home'))

        # Displays an error if the credentials are incorrect.
        flash('Invalid email or password. Please try again.')
        return redirect(url_for('admin_login'))

    # Displays the login page for a GET request.
    return render_template('admin_login.html')


# ----------------------------------------------------------
# Homepage Dashboard
# Accessible only after a successful administrator login.
# ----------------------------------------------------------
@app.route('/home')
def home():

    # Prevent unauthorised access to the dashboard.
    if not session.get('admin_logged_in'):
        flash('Please log in to access the dashboard.')
        return redirect(url_for('admin_login'))

    return render_template('homepage.html')


# ----------------------------------------------------------
# Stock Tracker
# Displays the stock-management interface.
#
# Future additions:
# - Read stock data from a database
# - Add, edit and delete stock records
# - Retrieve available suppliers from an API
# ----------------------------------------------------------
@app.route('/stock-tracker')
def stock_tracker():

    # Prevent unauthorised users from opening the stock tracker.
    if not session.get('admin_logged_in'):
        flash('Please log in to access the stock tracker.')
        return redirect(url_for('admin_login'))

    return render_template('stock_tracker.html')


# ----------------------------------------------------------
# Forgot Password
# Displays developer contact information for password help.
# ----------------------------------------------------------
@app.route('/forgot-password')
def forgot_password():

    return render_template('forgot_password.html')


# ----------------------------------------------------------
# Starts the Flask development server.
# ----------------------------------------------------------
if __name__ == '__main__':

    app.run(debug=True)
    