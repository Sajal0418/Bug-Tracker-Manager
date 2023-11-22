
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re


app = Flask(__name__)


app.secret_key = 'your secret key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Murakami@29'
app.config['MYSQL_DB'] = 'bugtracker'

mysql = MySQL(app)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['role'] = account['role']
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            msg = 'Logged in successfully !'
            return render_template('index.html', msg=msg)
        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg=msg)

def get_all_issues():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM issues")
    issues = cursor.fetchall()
    cursor.close()
    return issues

# Assuming you have a function to retrieve all users from the database
def get_all_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM accounts")
    users = cursor.fetchall()
    cursor.close()
    return users


@app.route('/logout')
def logout():
	session.pop('loggedin', None)
	session.pop('id', None)
	session.pop('username', None)
	return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check if the registration is for an admin
        is_admin = 'admin' in request.form.get('role', '').lower()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Set the role based on admin registration
            role = 'admin' if is_admin else 'user'

            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s, %s)',
                           (username, password, email, role))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'

    return render_template('register.html', msg=msg)



@app.route('/issues')
def display_issues():
    if 'loggedin' in session:
        # Connect to the MySQL database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Execute a simple query to retrieve all issues
        cursor.execute("SELECT * FROM issues")
        issues = cursor.fetchall()
        cursor.close()

        return render_template('issues.html', issues=issues)
    else:
        # Redirect to the login page if the user is not logged in
        return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    # Check if the user is logged in and has admin role
    if 'loggedin' in session and session['role'] == 'admin':
        # Retrieve issues and users data (modify as needed based on your data structure)
        issues = get_all_issues()  # Replace with your function to retrieve issues
        users = get_all_users()    # Replace with your function to retrieve users

        return render_template('admin.html', issues=issues, users=users)
    else:
        # Redirect to login if not logged in or not an admin
        return redirect(url_for('login'))

@app.route('/assign_issues', methods=['POST'])
def assign_issues():
    # Check if the user is logged in and has admin role
    if 'loggedin' in session and session['role'] == 'admin':
        # Get the issue_id and assigned_to from the form submission
        issue_id = request.form.get('issue_id')
        assigned_to = request.form.get('assigned_to')

        # Ensure assigned_to is an integer or set to NULL if not provided
        assigned_to = int(assigned_to) if assigned_to else None

        # Update the assigned_to column in the issues table
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE issues SET assigned_to = %s WHERE id = %s',
                       (assigned_to, issue_id))
        mysql.connection.commit()
        cursor.close()

        # Redirect to the admin dashboard
        return redirect(url_for('admin_dashboard'))
    else:
        # Redirect to login if not logged in or not an admin
        return redirect(url_for('login'))


@app.route('/logs')
def display_logs():
	if 'loggedin' in session:
		cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT logs.id AS logs_id, commit_message, username, title AS issue_title FROM logs JOIN accounts ON logs.userID = accounts.id JOIN issues ON logs.issueID = issues.id;")
		logs=cursor.fetchall()
		cursor.close()
		return render_template('logs.html', logs=logs)
	else:
		return redirect(url_for('login'))
	

@app.route('/profile')
def profile():
    # Check if the user is logged in
    if 'loggedin' in session:
        # Connect to the MySQL database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Retrieve the user's assigned issues
        user_id = session['id']
        cursor.execute(
            "SELECT * FROM issues WHERE assigned_to = %s", (user_id,))
        assigned_issues = cursor.fetchall()

        # Close the cursor (no need to close the connection as it's managed by Flask-MySQL)
        cursor.close()

        return render_template('profile.html', issues=assigned_issues)
    # If not logged in, redirect to the login page
    return redirect(url_for('login'))


@app.route('/change_status/<int:issue_id>', methods=['POST'])
def change_status(issue_id):
    if 'loggedin' in session:
        user_id = session['id']
        new_status = request.form['new_status']
        cursor = mysql.connection.cursor()
        update_query = "UPDATE issues SET status = %s WHERE id = %s AND assigned_to = %s"
        cursor.execute(update_query, (new_status, issue_id, user_id))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('display_issues'))
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
