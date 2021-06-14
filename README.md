# latoken_test
Saul Maldonado: Test for hiring process for python position @LAToken

Create a Virtual Environment with python 3.8

Dependencies:

        - run: pip install -r dependencies.txt

Architecture:

latoken_connector:
        - Based on Flask
        - execute run_connector.py

        Behaviour:
        - Will connect to LAToken and get Market data for BTC/USDT
        - WIll compare a target price with current market price
        - Will inclrease 1000€ evarytime it finds a higher market price
        - Evantually will execute a MARKET order to BUY 
        - Will fail to place the order if the wallet has unsufficient funds 
                - If so, it'll start to compare prices from original target_price
                - If the order is placed seccessfully the connector will automatically shutdown.

server: (under development)
        - executed with run_server.py
        - websocket service based on Flask running at ws://localhost:1234 for saving market data and to
          start, stop and run latoken connector



Scalation: implement Docker
           
