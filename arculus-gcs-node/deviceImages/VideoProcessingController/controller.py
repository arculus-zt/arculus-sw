import requests
import time
import math
import json
import sys
import os
from Crypto.Cipher import AES
import base64
import types
import warnings

warnings.filterwarnings("ignore")

NOAUTH = 'NOAUTH';
AUTH_TOKEN_BASED = 'AUTH_TOKEN_BASED';
AUTH_CERT_BASED = 'AUTH_CERT_BASED';


def pad(text):
    padding_len = 16 - (len(text) % 16)
    return text + chr(padding_len) * padding_len

def unpad(text):
    padding_len = ord(text[-1])
    return text[:-padding_len]

def encrypt(plaintext: str, AES_KEY, AES_IV) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(plaintext)
    encrypted = cipher.encrypt(padded.encode())
    return base64.b64encode(encrypted).decode()

def decrypt(ciphertext_b64: str, AES_KEY, AES_IV) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = base64.b64decode(ciphertext_b64)
    decrypted_padded = cipher.decrypt(encrypted).decode()
    return unpad(decrypted_padded)


try:
    with open('deviceMap.json', 'r') as file:
        deviceMap = json.load(file)
except FileNotFoundError:
    deviceMap = {}

def make_post_request(ip, url, data):
    AUTH_MODE = NOAUTH
    DEVICE_NAME = None
    AES_KEY, AES_IV = None, None
    if ip in deviceMap:
        AUTH_MODE = deviceMap[ip][1]
        DEVICE_NAME = deviceMap[ip][0]
        
    if AUTH_MODE == AUTH_TOKEN_BASED:
        try:
            with open(f'{DEVICE_NAME}_key.txt', 'r') as f:
                AES_KEY, AES_IV = f.read().strip().split('\n')
                AES_KEY = bytes(AES_KEY, 'utf-8')
                AES_IV = bytes(AES_IV, 'utf-8')
        except FileNotFoundError:
            print(f"Key file for {DEVICE_NAME} not found. so switching to NOAUTH mode.")
            AUTH_MODE = NOAUTH

    if AUTH_MODE == AUTH_TOKEN_BASED:
        data = {"encrypted": encrypt(json.dumps(data), AES_KEY, AES_IV)}
        response = requests.post(url, json=data)
        json_response = response.json()
        if 'encrypted' in json_response:
            decrypted_response = decrypt(json_response['encrypted'], AES_KEY, AES_IV)
            response._content = bytes(decrypted_response, 'utf-8')
    elif AUTH_MODE == AUTH_CERT_BASED:
        response = requests.post(
            url.replace("http://", "https://"),
            json=data, 
            cert=("/certs/client.cert.pem", "/certs/client.key.pem"),  # Client certificate and key
            verify=False
            # verify="/certs/ca.cert.pem"  # Verify server cert against CA)
        )
    else:
        response = requests.post(url, json=data)


    return response
   



# File path for saving mission state
MISSION_STATE_FILE = "mission_state.json"
LOG_FILE = "mission_log.txt"

def clear_log_file():
    with open(LOG_FILE, "w") as f:
        f.write("")  # Clears the file contents

# Check if log file exists and clear it
if os.path.exists(LOG_FILE):
    clear_log_file()

# Redirect stdout to the log file
log_file = open(LOG_FILE, "a")
sys.stdout = log_file

if len(sys.argv) != 8:
    print("Usage: python script.py initX initY destX destY survIp supIp relayIp")
    sys.exit(1)

# Parse command-line arguments
initX, initY, destX, destY = map(float, sys.argv[1:5])
survIp, supIp, relayIp = map(str, sys.argv[5:8])

survX, survY, supX, supY, relayX, relayY = initX, initY, initX, initY, initX, initY
relayDestX, relayDestY = 0, 0
returnFlag = 1
turnPointX, turnPointY = None, None
enemyFound = False
enemyX, enemyY = None, None
survHome = False
turnpointReached = False  
survPath = []
supPath = []
relayPath = []
enemyRadius = 0
missionSuccess = False
survCommLost = False
supCommLost = False
survCommEst = False
supCommEst = False

# Function to update mission state and store in JSON file
def update_mission_state():
    mission_state = {
        "survX": survX,
        "survY": survY,
        "supX": supX,
        "supY": supY,
        "enemyFound": enemyFound,
        "survHome": survHome,
        "enemyX": enemyX,
        "enemyY": enemyY,
        "supPath": supPath,
        "survPath": survPath,
        "relayPath": relayPath,
        "enemyRadius": enemyRadius,
        "destX": destX,
        "destY": destY,
        "missionSuccess": missionSuccess,
        "survCommLost": survCommLost,
        "supCommLost": supCommLost,
        "relayX": relayX,
        "relayY": relayY,
        "survCommEst": survCommEst,
        "supCommEst": supCommEst
        # Add other variables as needed
    }
    with open(MISSION_STATE_FILE, "w") as f:
        json.dump(mission_state, f)

def clear_mission_state():
    with open(MISSION_STATE_FILE, "w") as f:
        f.write("")

def is_home(x, y, move_distance):
    distance = math.sqrt((x - initX)**2 + (y - initY)**2)
    return returnFlag == -1 and distance <= move_distance

def comm_established(x, y, destX, destY, move_distance):
    distance = math.sqrt((x - destX)**2 + (y - destY)**2)
    return distance <= move_distance

def turnpoint_reached(x, y, move_distance):
    distance = math.sqrt((x - turnPointX)**2 + (y - turnPointY)**2)
    return distance <= move_distance

def dest_reached(x, y, move_distance):
    distance = math.sqrt((x - destX)**2 + (y - destY)**2)
    return distance <= move_distance

def command_to_move(x_coord, y_coord, move_distance, slope):
    # Calculate angle from slope
    angle = math.atan(slope)
    new_x = x_coord + move_distance * math.cos(angle)
    new_y = y_coord + move_distance * math.sin(angle)    
    # Update coordinates
    return new_x, new_y

# Start the mission by making a POST request to the first server
response = make_post_request(survIp, f'http://{survIp}:3050/startMission', {'initX': initX, 'initY': initY, 'destX': destX, 'destY': destY})
if response.ok:
    # Continue if response is OK
    make_post_request(supIp, f'http://{supIp}:4050/startMission', {'initX': initX, 'initY': initY})
    
    # Calculate the destination direction
    destinationDirection = (destY - initY) / (destX - initX) if (destX - initX) != 0 else -24
    survMoveCommand = f'http://{survIp}:3050/commandToMove'
    supMoveCommand = f'http://{supIp}:4050/commandToMove'
    # Start the movement loop
    while True:

        survPath.append({'x': survX, 'y': survY})
        with open('survState.txt', 'r') as file:
            survState = file.read().strip()
        with open('spoofGpsSurv.txt', 'r') as file:
            survSpoof = file.read().strip()

        if survSpoof != "":
            tokens = survSpoof.split(',')
            slope = -24 if tokens[0] == "null" else float(tokens[0])
            distance = -24 if tokens[1] == "null" else float(tokens[1])
            response = make_post_request(survIp, survMoveCommand, {'slope': slope, 'distance': distance})   
            response_data = response.json()
            if response.ok:
                if response_data.get('message') == "Moved":
                    # Update coordinates if moved
                    survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                    if returnFlag == -1:
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24
                    else:
                        destinationDirection = (destY - survY) / (destX - survX) if (destX - survX) != 0 else -24
            with open('spoofGpsSurv.txt', 'w') as file:
                file.write("")
            time.sleep(1)

        elif survState == 'connected':
            response = make_post_request(survIp, survMoveCommand, {'slope': destinationDirection, 'distance': 40 * returnFlag})
            response_data = response.json()
            if response.ok:
                if response_data.get('message') == "Moved":
                    # Update coordinates if moved
                    survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                    if returnFlag != -1:
                        destinationDirection = (destY - survY) / (destX - survX) if (destX - survX) != 0 else -24
                    else:
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24

                elif response_data.get('message') == "Found air defense":
                    # Update turn point and enemy coordinates if air defense is found
                    print("Found Air Defense")
                    returnFlag = -1
                    destinationDirection = (survY - initY) / (survX - initX) if (survX - initX) != 0 else -24
                    turnPointX, turnPointY = response_data.get('TURN_POINT_X'), response_data.get('TURN_POINT_Y')
                    enemyX, enemyY, enemyRadius = response_data.get('ENEMY_X'), response_data.get('ENEMY_Y'), response_data.get('ENEMY_RADIUS')
                    enemyFound = True
                    
                elif response_data.get('message') == "Reached Destination":
                    # Update flag if destination is reached
                    print("Reached Destination")
                    destinationDirection = (destY - survY) / (destX - survX) if (destX - survX) != 0 else -24
                    returnFlag = -1

        else:
            survCommLost = True
            relayDestX, relayDestY = (initX + survX)/2, (initY + survY)/2
            while True:
                relayPath.append({'x': relayX, 'y': relayY})
                lastFoundDirection = (relayDestY - relayY) / (relayDestX - relayX) if (relayDestX - relayX) != 0 else -24
                # print("relayX: ", relayX, ", relayY: ", relayY)  # Print surveillance drone coordinates
                
                relayX, relayY = command_to_move(relayX, relayY, 40, lastFoundDirection)
                time.sleep(1)
                update_mission_state()

                if comm_established(relayX, relayY, relayDestX, relayDestY, 40):
                    for step in range(2):
                        relayX, relayY = command_to_move(relayX, relayY, 40, -1/lastFoundDirection)
                        relayPath.append({'x': relayX, 'y': relayY})
                        survCommEst = True
                        update_mission_state()
                        time.sleep(1)
                    with open('survState.txt', 'w') as file:
                        file.write("connected")
                    # survCommEst = True
                    # print("Relay Communication Established")
                    # survMoveCommand = f'http://{relayIp}:5050/relayBridge?dest={survIp}:3050'
                    break
        
        if is_home(survX, survY, 40):
            print("Surveillance Drone reached home")
            survHome = True
            break
        
        time.sleep(1)
        update_mission_state()

    # while True:
    #     if not enemyFound:
    #         destinationDirection = (destY - supY) / (destX - supX) if (destX - supX) != 0 else -24
    #         turnpointReached = True
    #     else:
    #         destinationDirection = (turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24

    #     # Update mission state
    #     supPath.append({'x': supX, 'y': supY})
    #     with open('supState.txt', 'r') as file:
    #         supState = file.read().strip()
        
    #     with open('spoofGpsSup.txt', 'r') as file:
    #         supSpoof = file.read().strip()

    #     if supSpoof != "":
    #         tokens = supSpoof.split(',')
    #         slope = -24 if tokens[0] == "null" else float(tokens[0])
    #         distance = -24 if tokens[1] == "null" else float(tokens[1])
    #         response = requests.post(supMoveCommand, json={'slope': slope, 'distance': distance})            
    #         response_data = response.json()
    #         if response.ok:
    #             if response_data.get('message') == "Moved":
    #                 # Update coordinates if moved
    #                 supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
    #                 destinationDirection = ((destY - supY) / (destX - supX) if (destX - supX) != 0 else -24) if turnpointReached else ((turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24)
    #         with open('spoofGpsSup.txt', 'w') as file:
    #             file.write("")
    #         time.sleep(1)
    #         continue

    #     if enemyFound and turnpoint_reached(supX, supY, 40) and not turnpointReached:
    #         print("Supply Drone turning")
    #         turnpointReached = True
    #         print('Line 258')
    #         destinationDirection = (destY - supY) / (destX - supX) if (destX - supX) != 0 else -24
        
    #     elif dest_reached(supX, supY, 40):
    #         missionSuccess = True
    #         with open('survState.txt', 'w') as file:
    #             file.write("connected")
    #         with open('supState.txt', 'w') as file:
    #             file.write("connected")
    #         print("Mission Success")
    #         update_mission_state()
    #         time.sleep(10)
    #         clear_mission_state()
    #         break

    #     if supState == 'connected':
    #         response = requests.post(supMoveCommand, json={'slope': destinationDirection, 'distance': 40})
    #         if response.ok:
    #             response_data = response.json()
    #             if response_data.get('message') == "Moved":
    #                 # Update coordinates if moved
    #                 supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
    #                 if enemyFound == False or turnpointReached:
    #                     print('Line 281')
    #                     destinationDirection = (destY - supY) / (destX - supX) if (destX - supX) != 0 else -24
    #                 else:
    #                     print('Line 284')
    #                     destinationDirection = (turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24
    #     else:
    #         time.sleep(5)
    #         with open('supState.txt', 'w') as file:
    #             file.write("connected")
        

    #     # Sleep for some time to avoid too frequent API calls
    #     time.sleep(1)
    #     update_mission_state()

    while True:
        # Until the turnpoint is reached, direct the supply drone towards the turnpoint.
        if not turnpointReached and enemyFound:
            destinationDirection = (turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24
        # Once the turnpoint is reached or if no enemy is detected, direct it towards the final destination.
        else:
            destinationDirection = (destY - supY) / (destX - supX) if (destX - supX) != 0 else -24

        supPath.append({'x': supX, 'y': supY})
        with open('supState.txt', 'r') as file:
            supState = file.read().strip()
        
        with open('spoofGpsSup.txt', 'r') as file:
            supSpoof = file.read().strip()

        if supSpoof != "":
            tokens = supSpoof.split(',')
            slope = -24 if tokens[0] == "null" else float(tokens[0])
            distance = -24 if tokens[1] == "null" else float(tokens[1])
            response = make_post_request(supIp, supMoveCommand, {'slope': slope, 'distance': distance})            
            response_data = response.json()
            if response.ok and response_data.get('message') == "Moved":
                # Update coordinates if moved
                supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
            with open('spoofGpsSup.txt', 'w') as file:
                file.write("")
            time.sleep(1)
            continue

        # If communication is lost, sleep for 5 seconds before attempting to proceed
        if supState != 'connected':
            time.sleep(5)  # Sleeps for 5 seconds when communication is lost
            with open('supState.txt', 'w') as file:
                file.write("connected")
            continue

        if enemyFound and not turnpointReached and turnpoint_reached(supX, supY, 40):
            print("Supply Drone turning at turnpoint")
            turnpointReached = True  # Mark that the turnpoint is reached

        elif dest_reached(supX, supY, 40):
            missionSuccess = True
            print("Mission Success")
            update_mission_state()
            time.sleep(10)
            clear_mission_state()
            break

        response = make_post_request(supIp, supMoveCommand, {'slope': destinationDirection, 'distance': 40})
        if response.ok:
            response_data = response.json()
            if response_data.get('message') == "Moved":
                # Update coordinates if moved
                supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')

        # Sleep for some time to avoid too frequent API calls
        time.sleep(1)
        update_mission_state()

        # Until the turnpoint is reached, direct the supply drone towards the turnpoint.
        if not turnpointReached and enemyFound:
            destinationDirection = (turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24
        # Once the turnpoint is reached or if there is no enemy, direct it towards the final destination.
        else:
            destinationDirection = (destY - supY) / (destX - supX) if (destX - supX) != 0 else -24

        supPath.append({'x': supX, 'y': supY})
        with open('supState.txt', 'r') as file:
            supState = file.read().strip()
        
        with open('spoofGpsSup.txt', 'r') as file:
            supSpoof = file.read().strip()

        if supSpoof != "":
            tokens = supSpoof.split(',')
            slope = -24 if tokens[0] == "null" else float(tokens[0])
            distance = -24 if tokens[1] == "null" else float(tokens[1])
            response = make_post_request(supIp, supMoveCommand, {'slope': slope, 'distance': distance})            
            response_data = response.json()
            if response.ok and response_data.get('message') == "Moved":
                # Update coordinates if moved
                supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
            with open('spoofGpsSup.txt', 'w') as file:
                file.write("")
            time.sleep(1)
            continue

        # Check if the turnpoint is reached and not yet marked as reached
        if enemyFound and not turnpointReached and turnpoint_reached(supX, supY, 40):
            print("Supply Drone turning at turnpoint")
            turnpointReached = True  # Mark that the turnpoint is reached

        elif dest_reached(supX, supY, 40):
            missionSuccess = True
            print("Mission Success")
            update_mission_state()
            time.sleep(10)
            clear_mission_state()
            break

        if supState == 'connected':
            response = make_post_request(supIp, supMoveCommand, {'slope': destinationDirection, 'distance': 40})
            if response.ok:
                response_data = response.json()
                if response_data.get('message') == "Moved":
                    # Update coordinates if moved
                    supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
            else:
                time.sleep(5)
                with open('supState.txt', 'w') as file:
                    file.write("connected")

        # Sleep for some time to avoid too frequent API calls
        time.sleep(1)
        update_mission_state()

else:
    print("Failed to start mission on the first server.")

log_file.close()

