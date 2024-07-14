from flask import Flask, flash, render_template, request, redirect, url_for, session, send_file
from flask_mysqldb import MySQL
import qrcode
import os
import pandas as pd
from datetime import datetime
import cv2
import pyzbar.pyzbar as pyzbar

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Configure db
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'qrcode'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


mysql = MySQL(app)

# Hardcoded admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Ensure the directories exist
os.makedirs('static/qr_codes', exist_ok=True)

@app.route('/')
def home():
    return redirect(url_for('user_login'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return 'Invalid credentials'
    return render_template('admin_login.html')

@app.route('/register', methods=['GET','POST'])
def user_register():
    if request.method == 'POST':
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        matric = request.form["matric"]
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(firstname, lastname, email, matric, password) VALUES(%s, %s, %s, %s, %s)", (firstname, lastname, email, matric, password))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('user_login'))
    return render_template('register.html')

    
@app.route('/login', methods=['GET','POST'])
def user_login():
    if request.method == 'POST':
        matric = request.form['matric']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE matric = %s AND password = %s", (matric, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['firstname'] + " " + user['lastname']
            session['matric'] = user['matric'] # Adjust as per your database structure
            flash('Login successful.', 'success')
            return redirect(url_for('user'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('user_login'))

    return render_template('login.html')


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    qr_path = None
    if request.method == 'POST':
        course_code = request.form['course_code']
        date = request.form['date']
        qr_data = f'{course_code},{date}'
        qr_img = qrcode.make(qr_data)
        qr_path = f'static/qr_codes/{course_code}_{date}.png'
        qr_img.save(qr_path)
        
        # Create or clear the attendance Excel file
        excel_path = f'{course_code}_{date}.xlsx'
        if not os.path.exists(excel_path):
            df = pd.DataFrame(columns=['Name', 'Registration No', 'Date', 'Time'])
            df.to_excel(excel_path, index=False)

    return render_template('admin_dashboard.html', qr_path=qr_path)

@app.route('/download_qr_code', methods=['POST'])
def download_qr_code():
    qr_path = request.form['qr_path']
    return send_file(qr_path, as_attachment=True)

@app.route('/delete_qr_code', methods=['POST'])
def delete_qr_code():
    qr_path = request.form['qr_path']
    if os.path.exists(qr_path):
        os.remove(qr_path)
    return redirect(url_for('admin_dashboard'))

@app.route('/user', methods=['GET', 'POST'])
def user():
    if 'username' not in session or 'matric' not in session:
        flash('You need to log in first', 'error')
        return redirect(url_for('login'))  # Ensure there's a login route

    if request.method == 'POST':
        course_code = request.form['course_code']
        date = datetime.now().date()
        qr_code_path = f'static/qr_codes/{course_code}_{date}.png'
        
        if not os.path.exists(qr_code_path):
            flash('QR code not found for this course', 'error')
            return redirect(url_for('user'))

        # Open the camera and scan for QR code
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            decoded_objects = pyzbar.decode(frame)
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                if qr_data == f'{course_code},{date}':
                    cap.release()
                    cv2.destroyAllWindows()
                    # Mark attendance
                    excel_path = f'{course_code}_{date}.xlsx'
                    new_data = pd.DataFrame({
                        'Name': [session['username']],
                        'Registration No': [session['matric']],
                        'Date': [datetime.now().date()],
                        'Time': [datetime.now().time()]
                    })
                    if os.path.exists(excel_path):
                        df = pd.read_excel(excel_path)
                        df = pd.concat([df, new_data], ignore_index=True)
                    else:
                        df = new_data
                    df.to_excel(excel_path, index=False)
                    flash('Attendance marked successfully', 'success')
                    return redirect(url_for('user'))
            cv2.imshow('QR Code Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        flash('QR code does not match or attendance not signed', 'error')
        return redirect(url_for('user'))

    return render_template('user.html', username=session['username'], matric=session['matric'])

@app.route('/attendance_files')
def attendance_files():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    files = os.listdir('.')
    attendance_files = [f for f in files if f.endswith('.xlsx')]
    return render_template('attendance_files.html', attendance_files=attendance_files)

@app.route('/delete_attendance_file', methods=['POST'])
def delete_attendance_file():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    file_name = request.form['file_name']
    if os.path.exists(file_name):
        os.remove(file_name)
        flash(f'{file_name} has been deleted.', 'success')
    else:
        flash(f'{file_name} not found.', 'error')
    
    return redirect(url_for('attendance_files'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('user_login'))

if __name__ == '__main__':
    app.run(debug=True)
