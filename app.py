from flask import Flask, render_template, request, redirect, url_for, flash, session

# Creates the Flask application
app = Flask(__name__)

# Secret key used for sessions and flash messages
app.secret_key = 'TiberOps2026'

# ----------------------------------------------------------
# Admin Login Page
# Handles displaying the login page and validating
# administrator login credentials.
# ----------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    # Check if the login form has been submitted
    if request.method == 'POST':

        # Retrieve user input from the login form
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate the administrator credentials
        if username == 'admin@timberops.com' and password == 'TimberOps2026':

            # Store the login session
            session['admin_logged_in'] = True

            return "Login Successful! Welcome to the Admin Dashboard."

        else:

            # Display an error message if login fails
            flash('Invalid email or password. Please try again.')

            return redirect(url_for('admin_login'))

    # Display the login page
    return render_template('admin_login.html')


# ----------------------------------------------------------
# Forgot Password Page
# Displays the developer's contact information so users
# can request a password reset.
# ----------------------------------------------------------
@app.route('/forgot-password')
def forgot_password():

    # Render the Forgot Password page
    return render_template('forgot_password.html')


# ----------------------------------------------------------
# Starts the Flask development server
# ----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
    