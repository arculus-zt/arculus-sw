from flask import Flask, request, jsonify, requests
import math
import random
import json
import base64
from cryptography.fernet import Fernet


myjsonify = jsonify


def load_secure_vault():
    """Load encryption keys from a file into a list."""
    try:
        with open('securevault_keychain.txt', 'r') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print("The file securevault_keychain.txt was not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def encrypt_json(data, encryptionKey):
    """Encrypt JSON data."""
    fernet = Fernet(encryptionKey.encode())
    # Data must be a string before being encoded to bytes for encryption
    data_bytes = json.dumps(data).encode()
    encrypted = fernet.encrypt(data_bytes)
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_json(encrypted_data, encryptionKey):
    """Decrypt JSON data."""
    fernet = Fernet(encryptionKey.encode())
    # Convert base64 string to bytes before decryption
    encrypted_data_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted_bytes = fernet.decrypt(encrypted_data_bytes)
    return json.loads(decrypted_bytes.decode())

def encrypt_by_secure_vault(data, key_indices):
    """Encrypt data using keys from secure_vault based on indices."""
    for index in reversed(key_indices):
        data = encrypt_json(data, secure_vault[index])
        print(f"Data after encryption with key {index}: {data}")  # Debugging output
    return data

def decrypt_by_secure_vault(data, key_indices):
    """Decrypt data using keys from secure_vault based on indices."""
    for index in key_indices:
        data = decrypt_json(data, secure_vault[index])
        print(f"Data after decryption with key {index}: {data}")  # Debugging output
    return data

secure_vault = load_secure_vault()

app = Flask(__name__)

X_COORD = None
Y_COORD = None

@app.route('/startMission', methods=['POST'])
def start_mission():
    global X_COORD, Y_COORD

    data = request.json
    X_COORD = data.get('initX', 5.1)
    Y_COORD = data.get('initY', 6.0)

    return myjsonify({"message": "Mission started", "X_COORD": X_COORD, "Y_COORD": Y_COORD})
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
    return myjsonify({"message": "Moved", "X_COORD": X_COORD, "Y_COORD": Y_COORD, "slope": slope})

@app.route('/relayBridge', methods=['POST'])
def relay_bridge():
    dest = request.args.get('dest')
    if not dest:
        return myjsonify({"error": "Destination not provided"}), 400

    data = request.json
    try:
        response = requests.post(f'http://{dest}', json=data)
        response_data = response.json()
        return myjsonify(response_data), response.status_code
    except requests.exceptions.RequestException as e:
        return myjsonify({"error": str(e)}), 500

@app.route('/getCoordinates', methods=['GET'])
def get_coordinates():
    return myjsonify({"X_COORD": X_COORD, "Y_COORD": Y_COORD})
 

 
import ssl
import os
from Crypto.Cipher import AES

SERVER_MODE_FILE = "server_mode.txt"
CURRENT_MODE = None
ENCRYPTION_KEY = "aes_encryption_key.txt"
AES_KEY = None
AES_IV = None

def get_encryption_key_and_iv():
    if os.path.exists(ENCRYPTION_KEY):
        with open(ENCRYPTION_KEY) as f:
            data = f.read().strip().lower()
        key, iv = data.split('\n')
        return key, iv    
    raise FileNotFoundError("Encryption key file not found.")
    

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()

def get_mode():
    if os.path.exists(SERVER_MODE_FILE):
        with open(SERVER_MODE_FILE) as f:
            return f.read().strip().lower()
    return "https"

@app.route('/switch')
def change_mech():
    mode = get_mode()
    if CURRENT_MODE != mode:
        shutdown_server()
    return "Switching to auth mechanism..."


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

if __name__ == '__main__':
    CURRENT_MODE = get_mode()
    
    if CURRENT_MODE == "http":
        print("Starting in HTTP mode...")
        app.run(host='0.0.0.0', port=5050)
        AES_KEY, AES_IV = get_encryption_key_and_iv()
        myjsonify = lambda data: jsonify({
            "encrypted": encrypt(json.dumps(data)),
        })
    else:
        print("Starting in HTTPS mode...")
        context = ssl.change_mech(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="/certs/client.cert.pem", keyfile="/certs/client.key.pem")
        context.load_verify_locations(cafile="/certs/ca.cert.pem")
        app.run(debug=True, host='0.0.0.0', port=5050)
        