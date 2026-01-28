import requests
import time
import math
import json
import sys
import os

# File path for saving mission state
MISSION_STATE_FILE = "mission_state.json"
LOG_FILE = "mission_log.txt"

def clear_log_file():
    with open(LOG_FILE, "w") as f:
        f.write("")

if os.path.exists(LOG_FILE):
    clear_log_file()

log_file = open(LOG_FILE, "a")
sys.stdout = log_file

if len(sys.argv) != 9:
    print("Usage: python script.py initX initY destX destY survIp supIp relayIp missionType")
    sys.exit(1)

initX, initY, destX, destY = map(float, sys.argv[1:5])
survIp, supIp, relayIp = map(str, sys.argv[5:8])
missionType = sys.argv[8]

print(f"Mission Type: {missionType}")
print(f"Destination: ({destX}, {destY})")

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
    angle = math.atan(slope)
    new_x = x_coord + move_distance * math.cos(angle)
    new_y = y_coord + move_distance * math.sin(angle)
    return new_x, new_y

response = requests.post(f'http://{survIp}:3050/startMission', json={'initX': initX, 'initY': initY, 'destX': destX, 'destY': destY, 'missionType': missionType})
if response.ok:
    requests.post(f'http://{supIp}:4050/startMission', json={'initX': initX, 'initY': initY})
    
    destinationDirection = (destY - initY) / (destX - initX) if (destX - initX) != 0 else -24
    survMoveCommand = f'http://{survIp}:3050/commandToMove'
    supMoveCommand = f'http://{supIp}:4050/commandToMove'
    
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
            response = requests.post(survMoveCommand, json={'slope': slope, 'distance': distance})
            response_data = response.json()
            if response.ok:
                if response_data.get('message') == "Moved":
                    survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                    if returnFlag == -1:
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24
                    else:
                        destinationDirection = (destY - survY) / (destX - survX) if (destX - survX) != 0 else -24
            with open('spoofGpsSurv.txt', 'w') as file:
                file.write("")
            time.sleep(1)

        elif survState == 'connected':
            response = requests.post(survMoveCommand, json={'slope': destinationDirection, 'distance': 40 * returnFlag})
            response_data = response.json()
            if response.ok:
                if response_data.get('message') == "Moved":
                    survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                    if returnFlag != -1:
                        destinationDirection = (destY - survY) / (destX - survX) if (destX - survX) != 0 else -24
                    else:
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24

                elif response_data.get('message') == "Found air defense":
                    print("Found Air Defense")
                    
                    if missionType == 'armed':
                        enemyX, enemyY = destX, destY
                        enemyRadius = 100
                        print(f"Armed Mission: Target at air base ({enemyX}, {enemyY})")
                        print("Surveillance drone reached target, turning back")
                        turnPointX, turnPointY = response_data.get('TURN_POINT_X'), response_data.get('TURN_POINT_Y')
                        enemyFound = True
                        survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                        returnFlag = -1
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24
                    else:
                        returnFlag = -1
                        survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                        destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24
                        turnPointX, turnPointY = response_data.get('TURN_POINT_X'), response_data.get('TURN_POINT_Y')
                        enemyX, enemyY, enemyRadius = response_data.get('ENEMY_X'), response_data.get('ENEMY_Y'), response_data.get('ENEMY_RADIUS')
                        print(f"Resupply Mission: Air defense detected at ({enemyX}, {enemyY}), turning back")
                        enemyFound = True
                    
                elif response_data.get('message') == "Reached Destination":
                    print("Surveillance Drone reached destination")
                    survX, survY = response_data.get('X_COORD'), response_data.get('Y_COORD')
                    if missionType == 'armed':
                        print(f"Armed Mission: Confirmed target at ({destX}, {destY})")
                    returnFlag = -1
                    destinationDirection = (initY - survY) / (initX - survX) if (initX - survX) != 0 else -24

        else:
            survCommLost = True
            relayDestX, relayDestY = (initX + survX)/2, (initY + survY)/2
            while True:
                relayPath.append({'x': relayX, 'y': relayY})
                lastFoundDirection = (relayDestY - relayY) / (relayDestX - relayX) if (relayDestX - relayX) != 0 else -24
                
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
                    break
        
        if is_home(survX, survY, 40):
            print("Surveillance Drone reached home")
            survHome = True
            break
        
        time.sleep(1)
        update_mission_state()

    while True:
        if missionType == 'armed':
            destinationDirection = (enemyY - supY) / (enemyX - supX) if (enemyX - supX) != 0 else -24
        else:
            if not turnpointReached and enemyFound:
                destinationDirection = (turnPointY - supY) / (turnPointX - supX) if (turnPointX - supX) != 0 else -24
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
            response = requests.post(supMoveCommand, json={'slope': slope, 'distance': distance})
            response_data = response.json()
            if response.ok and response_data.get('message') == "Moved":
                supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')
            with open('spoofGpsSup.txt', 'w') as file:
                file.write("")
            time.sleep(1)
            continue

        if supState != 'connected':
            time.sleep(5)
            with open('supState.txt', 'w') as file:
                file.write("connected")
            continue

        if missionType == 'resupply' and enemyFound and not turnpointReached and turnpoint_reached(supX, supY, 40):
            print("Supply Drone turning at turnpoint")
            turnpointReached = True

        if missionType == 'armed':
            mission_complete = math.sqrt((supX - enemyX)**2 + (supY - enemyY)**2) <= 40
            if mission_complete:
                print(f"Armed Payload Drone reached target at ({enemyX}, {enemyY})")
        else:
            mission_complete = dest_reached(supX, supY, 40)
            if mission_complete:
                print(f"Supply Drone reached destination at ({destX}, {destY})")

        if mission_complete:
            missionSuccess = True
            print("Mission Success")
            update_mission_state()
            time.sleep(10)
            clear_mission_state()
            break

        response = requests.post(supMoveCommand, json={'slope': destinationDirection, 'distance': 40})
        if response.ok:
            response_data = response.json()
            if response_data.get('message') == "Moved":
                supX, supY = response_data.get('X_COORD'), response_data.get('Y_COORD')

        time.sleep(1)
        update_mission_state()

else:
    print("Failed to start mission on the first server.")

log_file.close()