from flask import Flask, render_template, request, jsonify
import requests
import base64
from datetime import datetime
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = Flask(__name__)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'sandbox').lower()
CONSUMER_KEY = os.getenv('CONSUMER_KEY', '')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET', '')
BUSINESS_SHORTCODE = os.getenv('BUSINESS_SHORTCODE', '')
PASSKEY = os.getenv('PASSKEY', '')
CALLBACK_URL = os.getenv('CALLBACK_URL', '')

SANDBOX_AUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
PRODUCTION_AUTH_URL = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
SANDBOX_STK_PUSH_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
PRODUCTION_STK_PUSH_URL = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

AUTH_URL = SANDBOX_AUTH_URL if ENVIRONMENT == 'sandbox' else PRODUCTION_AUTH_URL
STK_PUSH_URL = SANDBOX_STK_PUSH_URL if ENVIRONMENT == 'sandbox' else PRODUCTION_STK_PUSH_URL


def normalize_phone(phone):
    phone = (phone or '').strip()
    if not phone:
        return ''
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if digits.startswith('254'):
        return digits
    if digits.startswith('0'):
        return '254' + digits[1:]
    if digits.startswith('+254'):
        return digits.replace('+', '')
    return '254' + digits


def get_access_token():
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        return None
    try:
        response = requests.get(AUTH_URL, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), timeout=30)
        data = response.json()
        if response.status_code != 200:
            print(f'M-Pesa auth failed: {data}')
            return None
        return data.get('access_token')
    except Exception as exc:
        print(f'Error getting access token: {exc}')
        return None


def initiate_stk_push(phone, amount, pin):
    if not BUSINESS_SHORTCODE or not PASSKEY or not CALLBACK_URL:
        return {'error': 'Missing Safaricom config. Set BUSINESS_SHORTCODE, PASSKEY, CALLBACK_URL in .env.'}

    access_token = get_access_token()
    if not access_token:
        return {'error': 'Failed to generate M-Pesa access token. Check CONSUMER_KEY and CONSUMER_SECRET.'}

    formatted_phone = normalize_phone(phone)
    if not formatted_phone:
        return {'error': 'Phone number is required.'}

    try:
        amount_value = int(float(amount))
    except ValueError:
        return {'error': 'Amount must be a number.'}

    if amount_value <= 0:
        return {'error': 'Amount must be greater than zero.'}

    if len(pin) < 4 or not pin.isdigit():
        return {'error': 'Please enter a valid PIN.'}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f'{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}'.encode()).decode('utf-8')

    payload = {
        'BusinessShortCode': BUSINESS_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': amount_value,
        'PartyA': formatted_phone,
        'PartyB': BUSINESS_SHORTCODE,
        'PhoneNumber': formatted_phone,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': 'MpesaLogin',
        'TransactionDesc': 'Mpesa Login Payment'
    }

    try:
        response = requests.post(
            STK_PUSH_URL,
            json=payload,
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            timeout=30
        )
        data = response.json()
        print(f'STK push response: {data}')
        return data
    except Exception as exc:
        print(f'Error initiating STK push: {exc}')
        return {'error': str(exc)}


@app.route('/')
def home():
    return render_template('login.html', show_pin=False)


@app.route('/login', methods=['POST'])
def login():
    action = request.form.get('action', 'validate')
    phone = (request.form.get('phone') or '').strip()
    amount = (request.form.get('amount') or '').strip()
    pin = (request.form.get('pin') or '').strip()

    if action == 'back':
        return render_template('login.html', phone=phone, amount=amount, show_pin=False)

    if not phone or not amount:
        return render_template('login.html', error='Please enter your phone number and amount.', show_pin=False)

    if not phone.isdigit() and not phone.startswith('+'):
        return render_template('login.html', error='Please enter a valid phone number.', phone=phone, amount=amount, show_pin=False)

    if len(phone.replace('+', '')) < 10 or len(phone.replace('+', '')) > 13:
        return render_template('login.html', error='Please enter a valid phone number.', phone=phone, amount=amount, show_pin=False)

    try:
        amount_value = float(amount)
    except ValueError:
        return render_template('login.html', error='Amount must be a valid number.', phone=phone, amount=amount, show_pin=False)

    if amount_value <= 0:
        return render_template('login.html', error='Amount must be greater than zero.', phone=phone, amount=amount, show_pin=False)

    if action == 'validate':
        return render_template('login.html', success='Enter your M-Pesa PIN to continue.', phone=phone, amount=amount, show_pin=True)

    if action == 'confirm':
        if not pin:
            return render_template('login.html', error='Please enter your M-Pesa PIN.', phone=phone, amount=amount, pin=pin, show_pin=True)

        if len(pin) < 4 or not pin.isdigit():
            return render_template('login.html', error='Please enter a valid 4-digit M-Pesa PIN.', phone=phone, amount=amount, pin=pin, show_pin=True)

        result = initiate_stk_push(phone, amount, pin)

        if 'error' in result:
            return render_template('login.html', error=result['error'], phone=phone, amount=amount, show_pin=False)

        response_code = str(result.get('ResponseCode', ''))
        if response_code == '0':
            return render_template(
                'login.html',
                success=f'Payment prompt sent to {normalize_phone(phone)}. Please authorize the payment on your phone.',
                phone=phone,
                amount=amount,
                show_pin=False
            )

        error_message = result.get('errorMessage') or result.get('ResponseDescription') or 'Failed to initiate M-Pesa payment.'
        return render_template('login.html', error=error_message, phone=phone, amount=amount, show_pin=False)

    return render_template('login.html', show_pin=False)


@app.route('/callback', methods=['POST'])
def callback():
    try:
        data = request.get_json(silent=True) or {}
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')

        if result_code == 0:
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = {item.get('Name'): item.get('Value') for item in callback_metadata.get('Item', [])}
            print(f'Payment successful: {items}')
        else:
            print(f'Payment failed: {result_code}')

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as exc:
        print(f'Callback error: {exc}')
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})


if __name__ == '__main__':
    app.run(debug=True)
