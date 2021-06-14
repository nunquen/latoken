import sys
sys.path.append('../')

from flask import Flask
import websockets
import asyncio
import json
from datetime import datetime as dt

import utils
from connectors import latoken_connector

app = Flask(__name__)

SERVER_VERSION = "v1.0"
SERVER_IP = 'localhost'
SERVER_PORT = 1234

EVENT_LIST = []

CONNECTORS = [{'connector_name': 'LATOKEN_PROVIDER',
                'thread': latoken_connector,
                'status': 'OFF',
                'has_market_data': True}]


# Main function to receive all requests
async def get_data(websocket, path):

    data = await websocket.recv()
    data = json.loads(data)
    print(f"Server.get_data Receiving: {str(data)}")

    # Validating data
    if data['client'] in ['LATOKEN_CONNECTOR']:

        save_data(data=data)

        await websocket.send(f"Data received")

        return

    # Implement microservice
    if data['client'] in ['MICROSERVICE']:
        if data['function'] == 'GET_EVENT':

            await websocket.send(json.dumps({"dummy_data": "some_value"}))

            return


def save_data(data=dict):

    #TODO: implement data reception
    print("Saving data")




def start_websocket():

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    start_server = websockets.serve(get_data, "localhost", SERVER_PORT, ssl=None)

    asyncio.get_event_loop().run_until_complete(start_server)

    # Starting all connectors
    start_connector('CONNECTOR_PROVIDER')

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        asyncio.get_event_loop().run_until_complete(asyncio.get_event_loop().shutdown_asyncgens())
        asyncio.get_event_loop().close()


def run_in_background():
    import threading

    global syncThread_server
    syncThread_server = threading.Thread(target=start_websocket, args=[], name='SYNC_Server')
    syncThread_server.setDaemon(True)
    print("About to start Server in background")
    syncThread_server.start()
    print("Server started in background")


def start_connector(connector_name):

    for c in CONNECTORS:
        if connector_name == c['connector_name'] and c['status'] == 'OFF':
            print(f"  Staring connector {connector_name}")
            c['status'] = 'ON'
            c['thread'].run()

#start_websocket()