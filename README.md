# Mpesa-login

This project now contains a simple Flask web app that validates required login details and redirects users to the official M-Pesa website after a valid submission.

## Features
- Required field validation
- Phone number validation
- Minimum password length enforcement
- Redirect to M-Pesa after successful submission

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

## Important note
This is a demo/front-end login flow. It does not connect to the real Safaricom M-Pesa API or securely store credentials. For a real production application, you need a secure backend and official Daraja/STK integration.
