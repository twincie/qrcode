from flask import Flask, flash, render_template, request, redirect, url_for, session, send_file
import qrcode
import os
import pandas as pd
from datetime import datetime
import cv2
import pyzbar.pyzbar as pyzbar

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Hardcoded admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Ensure the directories exist
os.makedirs('static/qr_codes', exist_ok=True)

@app.route('/')
def home():
    return redirect(url_for('user'))

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
        # excel_path = f'{course_code}_{date}.xlsx'
        if os.path.exists(excel_path):
            print("Attandance already exists")
        else:
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
    if request.method == 'POST':
        name = request.form['name']
        registration_no = request.form['registration_no']
        course_code = request.form['course_code']
        date = datetime.now().date()
        qr_code_path = f'static/qr_codes/{course_code}_{date}.png'
        
        if not os.path.exists(qr_code_path):
            flash('QR code not found for this course and date', 'error')
            return redirect(url_for('user'))
            # return 'QR code not found for this course and date'

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
                        'Name': [name],
                        'Registration No': [registration_no],
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
                    # return 'Attendance marked successfully'
            cv2.imshow('QR Code Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        flash('QQR code does not match or attendance not signed', 'error')
        return redirect(url_for('user'))
        # return 'QR code does not match or attendance not signed'
    
    return render_template('user.html')

if __name__ == '__main__':
    app.run(debug=True)
