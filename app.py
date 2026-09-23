from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('login.html', show_pin=False)


@app.route('/login', methods=['POST'])
def login():
    phone = (request.form.get('phone') or '').strip()
    amount = (request.form.get('amount') or '').strip()
    pin = (request.form.get('pin') or '').strip()

    if not phone or not amount:
        return render_template('login.html', error='Please enter your phone number and amount.', show_pin=False)

    if not phone.isdigit() or len(phone) < 10 or len(phone) > 13:
        return render_template('login.html', error='Please enter a valid phone number.', phone=phone, amount=amount, show_pin=False)

    try:
        amount_value = float(amount)
    except ValueError:
        return render_template('login.html', error='Amount must be a valid number.', phone=phone, amount=amount, show_pin=False)

    if amount_value <= 0:
        return render_template('login.html', error='Amount must be greater than zero.', phone=phone, amount=amount, show_pin=False)

    if not pin:
        return render_template('login.html', success='Enter your M-Pesa PIN to continue.', phone=phone, amount=amount, show_pin=True)

    if len(pin) < 4:
        return render_template('login.html', error='Please enter a valid M-Pesa PIN.', phone=phone, amount=amount, pin=pin, show_pin=True)

    return render_template('login.html', success='M-Pesa PIN accepted. Payment request is being processed.', phone=phone, amount=amount, show_pin=True)


if __name__ == '__main__':
    app.run(debug=True)
