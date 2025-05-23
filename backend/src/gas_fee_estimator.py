'''
This script estimates the gas fee for a transaction on the Ethereum mainnet.
'''

# third party imports
from web3 import Web3
import dotenv
from requests.auth import HTTPBasicAuth
import os
import sys
from constants import ALCHEMY_KEY

if os.path.exists(".env"):
    dotenv.load_dotenv(".env")

INFURA_SECRET = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"

if not ALCHEMY_KEY:
    print("Please provide an infura key as an environment variable.")
    sys.exit()

# this is the current minimum gas required for a transaction on the Ethereum mainnet, but may change in the future
MINIMUM_GAS = 21_000

# get the gas price from the Ethereum mainnet using Web3 and Infura
def get_gas_price() -> float:
    # connect to the Ethereum mainnet
    # put your own infura node here
    w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
    # get the gas price
    gas_price = w3.eth.gas_price
    # convert the gas price to gwei
    gas_price_gwei = w3.from_wei(gas_price, 'gwei')
    # return the gas price in gwei
    # print(gas_price_gwei)
    return gas_price_gwei

def get_gas_fee() -> float:
    # get the gas price in gwei
    gas_price_gwei = get_gas_price()
    # calculate the gas fee
    gas_fee = gas_price_gwei * MINIMUM_GAS
    # return the gas fee
    # print(gas_fee)
    return gas_fee

def get_gas_fee_in_eth() -> float:
    # get the gas fee in gwei
    gas_fee_gwei = get_gas_fee()
    # convert the gas fee to eth
    gas_fee_eth = gas_fee_gwei / 1_000_000_000
    # return the gas fee in eth
    # print(gas_fee_eth)
    return float(gas_fee_eth)