# Mpesa-login

This project contains a Flask app for validating login details and initiating a real Safaricom M-Pesa STK Push transaction when the required M-Pesa credentials are configured.

## What this does
- Validates required user details
- Checks phone number format and password length
- Sends a real M-Pesa STK Push prompt to the entered phone number using the Safaricom Daraja API
- Returns a success message after the prompt is sent

## Important note
There is no public browser login API for M-Pesa accounts. The secure, supported way is to use Safaricom Daraja APIs with an STK Push prompt or a backend verification flow.

## Environment variables
Before running, set these variables in your environment or `.env` file:

```bash
export MPESA_CONSUMER_KEY="your_consumer_key"
export MPESA_CONSUMER_SECRET="your_consumer_secret"
export MPESA_SHORTCODE="174379"
export MPESA_PASSKEY="your_passkey"
export MPESA_CALLBACK_URL="https://your-domain.com/mpesa/callback"
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## Notes for production
- Never store app user passwords in plain text.
- Keep credentials in environment variables or a secrets manager.
- Use the Safaricom sandbox for testing and the live credentials for production.
- Always verify the callback payload from Safaricom before completing any real login or payment flow.
