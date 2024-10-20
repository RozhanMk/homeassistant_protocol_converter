import paho.mqtt.client as mqtt
import serial
import time
from settings import *
import json
STAND_LIGHTS_TOPIC_COMMANDS = {
    STAND_LIGHT1_COMMAND_TOPIC: [5, 1, 1],
    STAND_LIGHT2_COMMAND_TOPIC: [5, 1, 2],
    STAND_LIGHT3_COMMAND_TOPIC: [5, 1, 4],
    STAND_LIGHT4_COMMAND_TOPIC: [5, 1, 8]
}
LIGHTS_TOPIC_COMMANDS = {
    LIGHT1_COMMAND_TOPIC: [126, 1, 1],
    LIGHT2_COMMAND_TOPIC: [126, 1, 2],
    LIGHT3_COMMAND_TOPIC: [126, 1, 4],
    LIGHT4_COMMAND_TOPIC: [126, 1, 8],
    LIGHT5_COMMAND_TOPIC: [126, 1, 16],
    LIGHT6_COMMAND_TOPIC: [126, 1, 32]
}

WIFI_TOPIC_COMMANDS = {
    WIFI1_COMMAND_TOPIC, WIFI2_COMMAND_TOPIC, WIFI3_COMMAND_TOPIC
}


general_mode = 0
wifi_poles = []
ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=0)  # test different timeouts

def initial_setup():
    pass
    
def on_connect(client, userdata, flags, reason_code):
    print(f"Connected to MQTT broker with result code {reason_code}")
    for topic in STAND_LIGHTS_TOPIC_COMMANDS.keys():
        client.subscribe(topic)
    for topic in LIGHTS_TOPIC_COMMANDS.keys():
        client.subscribe(topic)
    for topic in WIFI_TOPIC_COMMANDS:
        client.subscribe(topic)
    client.subscribe(WNodes_Subscribe)
    client.subscribe(MODE_COMMAND_TOPIC)
    client.subscribe(FAN_COMMAND_TOPIC)
    client.subscribe(TEMP_COMMAND_TOPIC)

def on_message(client, userdata, msg):
    print(f"Message received: {msg.topic} {msg.payload.decode()}")
    if msg.topic in STAND_LIGHTS_TOPIC_COMMANDS:    # 4 stand lights
        stand_light_commands = {
            "1": STAND_LIGHTS_TOPIC_COMMANDS.get(msg.topic),
            "0": [STAND_LIGHTS_TOPIC_COMMANDS.get(msg.topic)[0] , 2, STAND_LIGHTS_TOPIC_COMMANDS.get(msg.topic)[2]]
        }
        command = stand_light_commands.get(msg.payload.decode())
        if command:
            send_can_message(command)
    elif msg.topic in LIGHTS_TOPIC_COMMANDS:    # 6 lights
        light_commands = {
            "1": LIGHTS_TOPIC_COMMANDS.get(msg.topic),
            "0": [LIGHTS_TOPIC_COMMANDS.get(msg.topic)[0] , 2, LIGHTS_TOPIC_COMMANDS.get(msg.topic)[2]]
        }
        command = light_commands.get(msg.payload.decode())
        if command:
            send_can_message(command)
    elif msg.topic == WNodes_Subscribe:
        msg_dict = json.loads(msg.payload.decode())
        update_wnode_dashboard(client, msg_dict)
    elif msg.topic in WIFI_TOPIC_COMMANDS:
        send_wifi_message(client, msg)
    elif msg.topic == MODE_COMMAND_TOPIC:
        mode = msg.payload.decode()
        set_mode(client, mode)
    elif msg.topic == FAN_COMMAND_TOPIC:
        fan_mode = msg.payload.decode()
        set_fan_mode(client, fan_mode)
    elif msg.topic == TEMP_COMMAND_TOPIC:
        temp = int(msg.payload.decode())
        set_temperature(client, temp)

def update_wnode_dashboard(client, msg):
    global wifi_poles
    wifi_poles = msg.get("poles")
    for index, status in enumerate(msg.get("poles"), start=1):
        update_light_status(index, status)

def update_light_status(light_number, status):
    if status == 1:
        client.publish(f"WNode/Light{light_number}/status", "1")
    else:
        client.publish(f"WNode/Light{light_number}/status", "0")


def send_wifi_message(client, msg):
    global wifi_poles
    if "Light1" in msg.topic:
        wifi_poles[0] = int(msg.payload.decode())
        curr_payload = {"poles":wifi_poles}
        client.publish(WNodes_Publish, json.dumps(curr_payload))
    elif "Light2" in msg.topic:
        wifi_poles[1] = int(msg.payload.decode())
        curr_payload = {"poles":wifi_poles}
        client.publish(WNodes_Publish, json.dumps(curr_payload))
    elif "Light3" in msg.topic:
        wifi_poles[2] = int(msg.payload.decode())
        curr_payload = {"poles":wifi_poles}
        client.publish(WNodes_Publish, json.dumps(curr_payload))

def set_mode(client, mode):
    print(f"Setting mode to {mode}")
    command = None
    if mode == "heat":
        command = [125, 7, 2]
    elif mode == "cool":
        command = [125, 7, 1]
    if command:
        send_can_message(command)
        client.publish(MODE_STATE_TOPIC, mode)

def set_fan_mode(client, fan_mode):
    print(f"Setting fan mode to {fan_mode}")
    command = None

    if fan_mode == "high":
        if (general_mode & 32) >> 5 == 1:
            command = [125, 0, general_mode - 32 + 3 - (general_mode & 3)]
        else:
            command = [125, 6, 3]
    elif fan_mode == "medium":
        if (general_mode & 32) >> 5 == 1:
            command = [125, 0, general_mode - 32 + 2 - (general_mode & 3)]
        else:
            command = [125, 6, 2]
    elif fan_mode == "low":
        if (general_mode & 32) >> 5 == 1:
            command = [125, 0, general_mode - 32 + 1 - (general_mode & 3)]
        else:
            command = [125, 6, 1]
    elif fan_mode == "off":
        if (general_mode & 32) >> 5 == 1:
            command = [125, 0, general_mode - 32 + 0 - (general_mode & 3)]
        else:
            command = [125, 6, 0]
    elif fan_mode == "auto":
        print(f"general mode = {general_mode}")
        if (general_mode & 32) >> 5 == 0:
            command = [125, 0, (general_mode + 32) - (general_mode & 3)]
    if command:
        send_can_message(command)
        client.publish(FAN_STATE_TOPIC, fan_mode)


def set_temperature(client, temp):
    print(f"Setting temperature to {temp}")
    command = [125, 3, int(temp*2)]
    send_can_message(command)
    client.publish(TEMP_STATE_TOPIC, int(temp))

def send_can_message(command):
    ser.write(command)
    ser.flush()


def publish_status(client):
    try:
        while True:
            if ser.in_waiting >= 5:
                line = ser.read(5)
                received_data = [int(x) for x in line]
            
                print(', '.join(map(str, received_data)))
                if received_data[:3] == [64, 5, 0] and received_data[4] == 37:  # 4 stand lights
                    stand_light_byte = received_data[3]
                    stand_light_statuses = {
                        STAND_LIGHT1_STATE_TOPIC: "1" if stand_light_byte & 1 else "0",
                        STAND_LIGHT2_STATE_TOPIC: "1" if stand_light_byte & 2 else "0",
                        STAND_LIGHT3_STATE_TOPIC: "1" if stand_light_byte & 4 else "0",
                        STAND_LIGHT4_STATE_TOPIC: "1" if stand_light_byte & 8 else "0"
                    }
                    for topic, status in stand_light_statuses.items():
                        client.publish(topic, status)
                elif received_data[:3] == [64, 126, 0] and received_data[4] == 37:  # 6 lights
                    light_byte = received_data[3]
                    light_statuses = {
                        LIGHT1_STATE_TOPIC: "1" if light_byte & 1 else "0",
                        LIGHT2_STATE_TOPIC: "1" if light_byte & 2 else "0",
                        LIGHT3_STATE_TOPIC: "1" if light_byte & 4 else "0",
                        LIGHT4_STATE_TOPIC: "1" if light_byte & 8 else "0",
                        LIGHT5_STATE_TOPIC: "1" if light_byte & 16 else "0",
                        LIGHT6_STATE_TOPIC: "1" if light_byte & 32 else "0"
                    }
                    for topic, status in light_statuses.items():
                        client.publish(topic, status)  
                elif received_data[:2] == [64, 125] and received_data[4] == 37: # Thermostat
                    publish_hvac_state(client, received_data)
                    
            
                
    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Stopping serial read.")
    finally:
        print("Serial reading port closed.")
        ser.close()

def publish_hvac_state(client, received_data):
    hvac_bytes = received_data[3]
    mode = None
    fan_mode = None
    if received_data[2] == 0:   # register 0
        if (hvac_bytes & 32) >> 5 == 1:
            fan_mode = "auto"
        else:
            if hvac_bytes & 3 == 0:
                    fan_mode = "off"
            elif hvac_bytes & 3 == 1:
                    fan_mode = "low"
            elif hvac_bytes & 3 == 2:
                    fan_mode = "medium"
            elif hvac_bytes & 3 == 3:
                    fan_mode = "high"
         
        if (hvac_bytes & 12) >> 2 == 1:
            mode = "cool"
        elif (hvac_bytes & 12) >> 2 == 2:
            mode = "heat"
        
        global general_mode
        general_mode = (hvac_bytes & 63)
        client.publish(MODE_STATE_TOPIC, mode)
        client.publish(FAN_STATE_TOPIC, fan_mode)

    if received_data[2] == 3:   # register 3
        set_temp = hvac_bytes //  2
        client.publish(TEMP_STATE_TOPIC, int(set_temp))
    if received_data[2] == 2:   # register 2
        current_temp = hvac_bytes
        client.publish(CURRENT_TEMP_TOPIC, current_temp)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start() #start the MQTT client in a separate thread

try:
    initial_setup()
    publish_status(client)
finally:
    client.loop_stop()
    client.disconnect()
