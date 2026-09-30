from flask import Flask, render_template, request, jsonify
import requests
import base64
from datetime import datetime
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = Flask(__name__)

# M-Pesa Credentials (Store these in .env file)
CONSUMER_KEY = os.getenv('CONSUMER_KEY', '')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET', '')
BUSINESS_SHORTCODE = os.getenv('BUSINESS_SHORTCODE', '174379')
PASSKEY = os.getenv('PASSKEY', '')
CALLBACK_URL = os.getenv('CALLBACK_URL', 'https://yourdomain.com/callback')

# M-Pesa API URLs
SANDBOX_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
PRODUCTION_AUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
PRODUCTION_STK_PUSH_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"


def get_access_token():
    """Get OAuth access token from Safaricom"""
    try:
        response = requests.get(
            SANDBOX_AUTH_URL,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
        )
        return response.json().get('access_token')
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None


def initiate_stk_push(phone, amount):
    """Initiate STK Push payment request"""
    try:
        access_token = get_access_token()
        if not access_token:
            return {'error': 'Failed to get access token'}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = BUSINESS_SHORTCODE + PASSKEY + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": BUSINESS_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": BUSINESS_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "MPesaLogin",
            "TransactionDesc": "M-Pesa Payment"
        }

        response = requests.post(STK_PUSH_URL, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Error initiating STK push: {e}")
        return {'error': str(e)}


@app.route('/')
def home():
    return render_template('login.html', show_pin=False)


@app.route('/login', methods=['POST'])
def login():
    action = request.form.get('action', 'validate')
    phone = (request.form.get('phone') or '').strip()
    amount = (request.form.get('amount') or '').strip()
    pin = (request.form.get('pin') or '').strip()

    # Back button - return to first step
    if action == 'back':
        return render_template('login.html', phone=phone, amount=amount, show_pin=False)

    # Validate phone and amount
    if not phone or not amount:
        return render_template('login.html', error='Please enter your phone number and amount.', show_pin=False)

    if not phone.isdigit() or len(phone) < 10 or len(phone) > 13:
        return render_template('login.html', error='Please enter a valid phone number (10-13 digits).', phone=phone, amount=amount, show_pin=False)

    try:
        amount_value = float(amount)
    except ValueError:
        return render_template('login.html', error='Amount must be a valid number.', phone=phone, amount=amount, show_pin=False)

    if amount_value <= 0:
        return render_template('login.html', error='Amount must be greater than zero.', phone=phone, amount=amount, show_pin=False)

    # If only validating phone/amount, show PIN section
    if action == 'validate':
        return render_template('login.html', success='Enter your M-Pesa PIN to continue.', phone=phone, amount=amount, show_pin=True)

    # Confirm PIN and process payment
    if action == 'confirm':
        if not pin:
            return render_template('login.html', error='Please enter your M-Pesa PIN.', phone=phone, amount=amount, pin=pin, show_pin=True)

        if len(pin) < 4 or not pin.isdigit():
            return render_template('login.html', error='Please enter a valid 4-digit M-Pesa PIN.', phone=phone, amount=amount, pin=pin, show_pin=True)

        # Initiate STK Push to M-Pesa
        result = initiate_stk_push(phone, amount)

        if 'error' in result:
            return render_template('login.html', error=f'Payment initiation failed: {result["error"]}', phone=phone, amount=amount, show_pin=False)

        # Check STK Push response
        if result.get('ResponseCode') == '0':
            success_msg = f'Payment prompt sent to {phone}. Please check your phone and enter your PIN on the M-Pesa popup.'
            return render_template('login.html', success=success_msg, phone=phone, amount=amount, show_pin=False)
        else:
            error_msg = result.get('ResponseDescription', 'Failed to initiate payment')
            return render_template('login.html', error=error_msg, phone=phone, amount=amount, show_pin=False)

    return render_template('login.html', show_pin=False)


@app.route('/callback', methods=['POST'])
def callback():
    """Handle Safaricom callback"""
    try:
        data = request.get_json()
        # Process payment result
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')

        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = {item['Name']: item['Value'] for item in callback_metadata.get('Item', [])}
            
            print(f"Payment successful! Details: {items}")
            # Save to database here
            
        else:
            # Payment failed
            print(f"Payment failed with code: {result_code}")

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        print(f"Callback error: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})


@app.route('/payment-status', methods=['GET'])
def payment_status():
    """Check payment status (optional endpoint)"""
    try:
        phone = request.args.get('phone')
        # Query database for payment status
        return jsonify({'status': 'pending', 'phone': phone})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
