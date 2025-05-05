import json
import os
from web3 import Web3
import time
from tqdm import tqdm  # progress bar
from constants import ALCHEMY_KEY

# Configuration
RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"  # Replace with your Ethereum RPC URL
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, '.', 'data_curve.json')
OUTPUT_FILE = os.path.join(BASE_DIR, '.', 'curve_pool_fees.json')
# Curve pool contract ABI (only the functions we need)
CURVE_POOL_ABI = [
    {
        "name": "fee",
        "outputs": [{"type": "uint256", "name": ""}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "offpeg_fee_multiplier",
        "outputs": [{"type": "uint256", "name": ""}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

def get_pool_addresses_from_graphql_results(file_path):
    """Extract unique pool addresses from GraphQL result file"""
    with open(file_path, 'r', encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract unique pool addresses
    pool_addresses = set()
    for item in data:
        if 'address' in item and item['address'].startswith('0x'):
            pool_addresses.add(Web3.to_checksum_address(item['address']))
    
    return list(pool_addresses)

def fetch_pool_fees(pool_addresses):
    """Fetch fee and offpeg_fee_multiplier for each pool"""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        raise Exception("Failed to connect to Ethereum node")
    
    results = {}
    
    for address in tqdm(pool_addresses, desc="Fetching pool fees"):
        try:
            pool_contract = w3.eth.contract(address=address, abi=CURVE_POOL_ABI)
            
            # Some pools might not have these methods, so we use try/except
            try:
                fee = pool_contract.functions.fee().call()
            except Exception as e:
                print(f"Error getting fee for {address}: {e}")
                fee = None
            
            try:
                offpeg_multiplier = pool_contract.functions.offpeg_fee_multiplier().call()
            except Exception as e:
                # print(f"Error getting offpeg_fee_multiplier for {address}: no offpeg_multiplier")
                offpeg_multiplier = 1
            
            results[address.lower()] = {
                "fee": fee,
                "offpeg_fee_multiplier": offpeg_multiplier
            }
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing pool {address}: {e}")
    
    return results

def save_to_json(data, output_file):
    """Save results to a JSON file"""
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {output_file}")

def main():
    # You can either hardcode addresses or extract them from a file
    # Option 1: Extract from a file

    pool_addresses = get_pool_addresses_from_graphql_results(DATA_FILE)
    
    print(f"Found {len(pool_addresses)} unique pool addresses")
    
    # Fetch fee data for each pool
    pool_fees = fetch_pool_fees(pool_addresses)
    
    # Save results
    save_to_json(pool_fees, OUTPUT_FILE)

if __name__ == "__main__":
    main()