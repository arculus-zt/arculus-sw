from flask import Flask, request, jsonify
import math
import random
app = Flask(__name__)

X_COORD = None
Y_COORD = None

myjsonify = jsonify

@app.route('/startMission', methods=['POST'])
def start_mission():
    global X_COORD, Y_COORD

    data = request.json
    X_COORD = data.get('initX', 5.1)
    Y_COORD = data.get('initY', 6.0)

    return jsonify({"message": "Mission started", "X_COORD": X_COORD, "Y_COORD": Y_COORD})
# , "TURN_POINT_X": TURN_POINT_X, "TURN_POINT_Y": TURN_POINT_Y

@app.route('/commandToMove', methods=['POST'])
def command_to_move():
    global X_COORD, Y_COORD
    data = request.json
    slope = data.get('slope', 0.0)
    move_distance = data.get('distance', 2)
    # Calculate angle from slope
    angle = math.atan(slope)
    new_x = X_COORD + move_distance * math.cos(angle)
    new_y = Y_COORD + move_distance * math.sin(angle)    
    # Update coordinates
    X_COORD = new_x
    Y_COORD = new_y
    return jsonify({"message": "Moved", "X_COORD": X_COORD, "Y_COORD": Y_COORD, "slope": slope})

@app.route('/relayBridge', methods=['POST'])
def relay_bridge():
    dest = request.args.get('dest')
    if not dest:
        return jsonify({"error": "Destination not provided"}), 400

    data = request.json
    try:
        response = requests.post(f'http://{dest}', json=data)
        response_data = response.json()
        return jsonify(response_data), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/getCoordinates', methods=['GET'])
def get_coordinates():
    return myjsonify({"X_COORD": X_COORD, "Y_COORD": Y_COORD})






 
import ssl
import os
from Crypto.Cipher import AES

SERVER_MODE_FILE = "auth_mode.txt"
CURRENT_MODE = None
ENCRYPTION_KEY = "/certs/key.txt"
AES_KEY = None
AES_IV = None

NOAUTH = 'NOAUTH';
AUTH_TOKEN_BASED = 'AUTH_TOKEN_BASED';
AUTH_CERT_BASED = 'AUTH_CERT_BASED';

import base64
def get_encryption_key_and_iv():
    if os.path.exists(ENCRYPTION_KEY):
        with open(ENCRYPTION_KEY) as f:
            data = f.read().strip().lower()
        key, iv = data.split('\n')
        return bytes(key, 'utf-8'), bytes(iv, 'utf-8')
    raise FileNotFoundError("Encryption key file not found.")
    
def get_mode():
    if os.path.exists(SERVER_MODE_FILE):
        with open(SERVER_MODE_FILE) as f:
            return f.read().strip()
    return NOAUTH


def pad(text):
    padding_len = 16 - (len(text) % 16)
    return text + chr(padding_len) * padding_len

def unpad(text):
    padding_len = ord(text[-1])
    return text[:-padding_len]

def encrypt(plaintext: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(plaintext)
    encrypted = cipher.encrypt(padded.encode())
    return base64.b64encode(encrypted).decode()

def decrypt(ciphertext_b64: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = base64.b64decode(ciphertext_b64)
    decrypted_padded = cipher.decrypt(encrypted).decode()
    return unpad(decrypted_padded)


modify_json = lambda data: data

@app.before_request
def modify_post_json():
    if request.method == "POST" and request.is_json:
        data = request.get_json()
        if data:
            data = modify_json(data)
            request._cached_json = data
            request.data = json.dumps(data).encode('utf-8')

if __name__ == '__main__':
    CURRENT_MODE = get_mode()
    if CURRENT_MODE == NOAUTH:
        myjsonify = jsonify
    elif CURRENT_MODE == AUTH_TOKEN_BASED:
        AES_KEY, AES_IV = get_encryption_key_and_iv()
        myjsonify = lambda data: jsonify({
            "encrypted": encrypt(json.dumps(data)),
        })
        modify_json = lambda data: json.loads(decrypt(data['encrypted'])) if 'encrypted' in data else data
        app.run(host='0.0.0.0', port=5050)
    elif CURRENT_MODE == AUTH_CERT_BASED:
        print("Starting in HTTPS mode...")
        context = ssl.change_mech(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="/certs/client.cert.pem", keyfile="/certs/client.key.pem")
        context.load_verify_locations(cafile="/certs/ca.cert.pem")
        app.run(host='0.0.0.0', port=5050)