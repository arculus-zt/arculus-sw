from flask import Flask, request, jsonify
import math

app = Flask(__name__)

# Global variables
X_COORD = None
Y_COORD = None
blocklist = []  # Initialize an empty list for blocked IP addresses

@app.route('/startMission', methods=['POST'])
def start_mission():
    global X_COORD, Y_COORD
    data = request.json
    X_COORD = data.get('initX', 5.1)
    Y_COORD = data.get('initY', 6.0)
    return jsonify({"message": "Mission started", "X_COORD": X_COORD, "Y_COORD": Y_COORD})

@app.route('/commandToMove', methods=['POST'])
def command_to_move():
    global X_COORD, Y_COORD
    data = request.json
    slope = data.get('slope', 0.0)
    move_distance = data.get('distance', 2)
    angle = math.atan(slope)
    new_x = X_COORD + move_distance * math.cos(angle)
    new_y = Y_COORD + move_distance * math.sin(angle)
    X_COORD = new_x
    Y_COORD = new_y
    return jsonify({"message": "Moved", "X_COORD": X_COORD, "Y_COORD": Y_COORD})

@app.route('/addToBlocklist', methods=['POST'])
def add_to_blocklist():
    ip = request.json.get('ip')
    if ip and ip not in blocklist:
        blocklist.append(ip)
        return jsonify({"message": f"{ip} added to blocklist"}), 200
    else:
        return jsonify({"message": "Invalid IP or already in blocklist"}), 400

@app.before_request
def check_ip_blocklist():
    requester_ip = request.remote_addr
    if requester_ip in blocklist:
        return jsonify({"message": "Forbidden access"}), 403

@app.route('/getCoordinates', methods=['GET'])
def get_coordinates():
    return jsonify({"X_COORD": X_COORD, "Y_COORD": Y_COORD})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4050)
