from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'TimberOps2026' 

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin@timberops.com' and password == 'TimberOps2026':
            session['admin_logged_in'] = True
            
            return "Login Successful! Welcome to the Admin Dashboard."
        else:
            flash('Invalid email or password. Please try again.')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True)