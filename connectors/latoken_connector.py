import sys

sys.path.append('../')

from flask import Flask

import threading
import time
import json
import websockets
import asyncio
import datetime
import requests
from requests.exceptions import ConnectionError, ConnectTimeout 
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum

app = Flask(__name__)

global syncThread_latoken_connector
global keep_running
keep_running = True

CONNECTOR_LOOP_TIMER = 6
SERVER_PORT = 1234
SERVER_URI = "ws://localhost:" + str(SERVER_PORT)
CLIENT = 'LATOKEN_CONNECTOR'


class LAToken:

    class Currency(Enum):
        USDC = '894f0a35-1f7e-4ff1-b1c1-1705b27d9dc2'
        BTC = '92151d82-df98-4d88-9a4d-284fa9eca49f'
        ETH = '620f2019-33c0-423b-8a9d-cde4d7f8ef7f'
        DAI = '269af7c2-5cb4-4720-b065-0430dd7a4d6b'
        USDT = '0c3a106d-bde3-4c13-a26e-3fd2394529e5'


    def __init__(self):

        self.apiSecret = 'YTdmYWViMDctOTZhOS00ZTRlLWI1ODctZjk1YzRiMTVhM2Rk'
        self.apiKey = 'ccceaf8a-16a1-42bd-8a41-37d0f8a71587'
        self.baseUrl = 'https://api.latoken.com'
        
        self.current_endpoint = ''
        self.current_date = ''
        self.data_event = None

        self.USDC = self.Currency.USDC
        self.BTC = self.Currency.BTC
        self.ETH = self.Currency.ETH
        self.DAI = self.Currency.DAI
        self.USDT = self.Currency.USDT

        self.target_prices = []
    
    def set_target_price(self, currency=str, quote=str, price=float):
        
        target_price = {
            "currency": currency, 
            "quote":quote, 
            "price":price
        }

        try:
            # Looking for saved target price to update its value
            saved_target_price = list(filter(lambda x: x['currency'] == currency and x['quote'] == quote, self.target_prices))
            # Getting saved target price index within array and updating value
            index = self.target_prices.index(saved_target_price[0])
            self.target_prices[index] = target_price

        except Exception:
            self.target_prices.append(target_price)

    def get_target_price(self, currency=str, quote=str):
        
        price = 0.0
        saved_target_price = list(filter(lambda x: x['currency'] == currency and x['quote'] == quote, self.target_prices))

        if len(saved_target_price) > 0:
            price = saved_target_price[0]['price']

        return price

    def __get_options():

        options = {}

        return options

    def __get_signature(self, method=str, endpoint=str, params=dict):
        
        queryParams = ''

        if params:
            serializeFunc = map(lambda it : it[0] + '=' + str(it[1]), params.items())
            queryParams = '&'.join(serializeFunc)

        # API FIX: must cast to bytes to make hmac to work
        signature = hmac.new(
            bytes(self.apiSecret, 'latin-1'), 
            bytes(method + endpoint + queryParams, 'latin-1'), 
            hashlib.sha512
        )
        return signature.hexdigest(), queryParams

    def get_time(self): 
        endpoint = '/v2/time'
        method = 'GET'

        server_time = 0

        try:
            response = requests.get(
                self.baseUrl + endpoint,
                headers = {}
            )
        except ConnectionError as ce:
            print("LAToken.get_time-> ConnectionError: " + str(ce))
            return 0

        if response.status_code == 200:
            server_time = json.loads(response.content)['serverTime']

            # ByPass: must devide by 1000 to reduce server_time (development made on Windows)
            server_time = server_time / 1000

            return datetime.fromtimestamp(server_time)
        
        return server_time

    def get_active_currencies(self):
        endpoint = '/v2/currency'
        method = 'GET'
        currencies = []

        try:
            response = requests.get(
                self.baseUrl + endpoint,
                headers = {}
            )
        except ConnectionError as ce:
            print("LAToken.get_active_currencies-> ConnectionError: " + str(ce))
            return []

        print(response.json)

        if response.status_code == 200:
            currencies = json.loads(response.content)

        return currencies
        

    def __get(self, endpoint=str, params={}):

        method = 'GET'

        signature, queryParams = self.__get_signature(method=method, endpoint=endpoint, params=params)

        try:

            response = requests.get(
                self.baseUrl + endpoint + '?' + queryParams if queryParams else self.baseUrl + endpoint,
                headers = {
                    'X-LA-APIKEY': self.apiKey,
                    'X-LA-SIGNATURE': signature,
                    'X-LA-DIGEST': 'HMAC-SHA512'
                }
            )

            if response.status_code == 200:
                response = json.loads(response.content)
            else:
                response = []
        except ConnectionError as ce:
            print("LAToken.__get-> ConnectionError: " + str(ce))
            raise ConnectionError()
            
        return response

    def __post(self, endpoint=str, params={}):

        method = 'POST'

        response = {"message":"unknown error. Default message"}

        signature, queryParams = self.__get_signature(method=method, endpoint=endpoint, params=params)

        try:

            response = requests.post(
                self.baseUrl + endpoint,
                headers = {
                    'Content-Type': 'application/json',
                    'X-LA-APIKEY': self.apiKey,
                    'X-LA-SIGNATURE': signature,
                    'X-LA-DIGEST': 'HMAC-SHA512'
                },
                json = params
            )

            if response.status_code == 200 or response.status_code == 400:
                response = json.loads(response.content)
            
        except ConnectionError as ce:
            print("LAToken.__post-> ConnectionError: " + str(ce))
            raise ConnectionError()
            
        return response

    def place_new_order(self, currency=str, quote=str, type=str, price=float, quantity=int):

        endpoint = '/v2/auth/order/place'

        params = {
            'baseCurrency': currency,
            'quoteCurrency': quote,
            'side': 'SELL',
            'condition': 'GOOD_TILL_CANCELLED',
            'type': 'LIMIT',
            'clientOrderId': 'myTestingOrder',
            'price': price,
            'quantity': quantity,
            'timestamp': int(datetime.now().timestamp()*1000)
        }
        
        try:
            response = self.__post(endpoint=endpoint, params=params)
        except ConnectionError as ce:
            response = []

        return response

    def get_balances(self):

        endpoint = '/v2/auth/account'
        method = 'GET'

        params = {
            'zeros': 'true'
        }
        
        try:
            response = self.__get(endpoint=endpoint, params=params)
        except ConnectionError as ce:
            response = []

        return response

    def get_balance_by_currency(self, currency=str):

        type = 'ACCOUNT_TYPE_WALLET'
        endpoint = f'/v2/auth/account/currency/{currency}/{type}'
        try:
            response = self.__get(endpoint=endpoint)
            response['available'] = float(response['available'])
            response['blocked'] = float(response['blocked'])
        except ConnectionError as ce:
            response = {}

        return response       

    def get_orders(self) :

        endpoint = '/v2/auth/order'
        params = {
            'from': int(datetime.now().timestamp()*1000),
            'limit': '50'
        }

        try:
            response = self.__get(endpoint=endpoint, params=params)
        except ConnectionError as ce:
            response = []

        return response    

    def get_book(self, currency=str, quote=str, limit=None):
        
        endpoint = f'/v2/book/{currency}/{quote}'
        method = 'GET'
        queryParams = None
        book = {}

        if limit:
            queryParams = f"limit={limit}"

        try:
            response = requests.get(
                self.baseUrl + endpoint + '?' + queryParams if queryParams else self.baseUrl + endpoint,
                headers = {}
            )
        except ConnectionError as ce:
            print("LAToken.get_book-> ConnectionError: " + str(ce))
            return []

        if response.status_code == 200:
            book = json.loads(response.content)

        return book

    def get_ticker(self, currency=str, quote=str):
        
        endpoint = f'/v2/ticker/{currency}/{quote}'
        method = 'GET'
        ticker = {}

        try:
            response = requests.get(
                self.baseUrl + endpoint,
                headers = {}
            )
        except ConnectionError as ce:
            print("LAToken.get_book-> ConnectionError: " + str(ce))
            return []

        if response.status_code == 200:
            ticker = json.loads(response.content)
            ticker['lastPrice'] = float(ticker['lastPrice'])
            ticker['volume24h'] = float(ticker['volume24h'])
            ticker['volume7d'] = float(ticker['volume7d'])
            ticker['change24h'] = float(ticker['change24h'])
            ticker['change7d'] = float(ticker['change7d'])

        return ticker

def set_keep_running(kp):
    global keep_running
    keep_running = kp


def get_keep_running():
    global keep_running
    return keep_running


async def send_data(data):

    if not get_keep_running():
        remote_stop()

    if data is None:
        return
        
    try:
        # NOTE: ping_interval=None is to help with error networking
        async with websockets.connect(SERVER_URI, ping_interval=None) as websocket:

            data['client'] = CLIENT

            data = json.dumps(data)

            await websocket.send(data)

            response = await websocket.recv()

            if response == "STOP_CONNECTOR":
                set_keep_running(False)

    except Exception as e:
        print("Can't connect to the server.... ")
        print("Exception: " + str(e))
        remote_stop()


def loop():

    exchange = LAToken()

    target_price_increase = 1000
    strike_price = 36000
    quantity = 100

    data = None

    print(f"Starting LAToken connector. Remote server time is {exchange.get_time()}")

    exchange.set_target_price(currency=exchange.BTC.value, quote=exchange.USDT.value, price=strike_price)

    while get_keep_running():
        print(f"inside while CONNECTOR_LOOP_TIMER is {CONNECTOR_LOOP_TIMER}")

        try:

            # Get wallet balances
            btc_balance = exchange.get_balance_by_currency(currency=exchange.BTC.value)

            # Get pair prices
            btc_usdt = exchange.get_ticker(currency=exchange.BTC.value, quote=exchange.USDT.value)

            # Place order and catch some responses or error
            if btc_balance and btc_usdt:

                last_price = btc_usdt['lastPrice']
                
                target_price = exchange.get_target_price(currency=exchange.BTC.value, quote=exchange.USDT.value)

                print(f"{exchange.BTC.name}/{exchange.USDT.name}: target_price is {target_price} and last_price is {last_price}")
               
                if target_price > last_price:
                    
                    print("Placing buying order at MARKET")
                    res = exchange.place_new_order(currency=exchange.Currency.BTC.value,
                                                    quote=exchange.Currency.USDT.value,
                                                    type='MARKET',
                                                    price=last_price,
                                                    quantity=quantity)
                    print(f"Order status is {res['status']}: {res['message']}")
                    if res['status'] == 'SUCCESS':
                        print("  Stopping LAToken connector. Mission accomplished")
                        remote_stop()
                    
                    elif res['status'] == 'FAILURE':
                        print(res)
                        print(f"  Setting target price back to {strike_price}. Waiting to get funds for trading.")
                        exchange.set_target_price(currency=exchange.BTC.value, quote=exchange.USDT.value, price=strike_price)

                    else:
                        print("  Stopping LAToken connector. Unexpected status received.")
                        remote_stop()

                else:
                    print("No opportunity found. Increasing target_price by 1000€")
                    exchange.set_target_price(currency=exchange.BTC.value, quote=exchange.USDT.value, price=(target_price + target_price_increase))
                
            # TODO: send data to server
            response = asyncio.get_event_loop().run_until_complete(send_data(data))

        except Exception as e:
            loop_task = asyncio.new_event_loop()
            asyncio.set_event_loop(loop_task)
            print("LATOKEN_CONNECTOR.LOOP.ERROR No loop detected, creating a new event loop")
            response = asyncio.get_event_loop().run_until_complete(send_data(data))

        
        time.sleep(CONNECTOR_LOOP_TIMER)


def run():

    print("Starting LATOKEN connector")
    set_keep_running(True)

    global syncThread_latoken_connector

    syncThread_latoken_connector = threading.Thread(target=loop, args=[], name='LAToken_Connector')
    syncThread_latoken_connector.setDaemon(True)
    print("About to start LAToken Connector in background")
    syncThread_latoken_connector.start()
    print("LAToken connector started in background")


def remote_stop():
    print("Received a remote Stopping signal. Shutting down LAToken connector")

    set_keep_running(False)

    global syncThread_latoken_connector

    if syncThread_latoken_connector:

        syncThread_latoken_connector.join(1)

