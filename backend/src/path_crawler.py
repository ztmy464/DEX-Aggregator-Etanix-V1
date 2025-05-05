'''
This module simulates the execution of potential swap paths found by the pathfinder.
It calculates the actual output amount, price impact, and estimated gas fees for each
step in a path, considering the specific DEX protocol of each pool.
It also includes logic to split trades across multiple paths to mitigate price impact.
'''

from simulateSwap import simulateSwap
from gas_fee_estimator import get_gas_fee_in_eth

import networkx as nx
from constants import MAX_ROUTES
import dotenv
import os

# ------------------------ Commented Out Code ------------------------
'''# Code to load CoinMarketCap API key and get token prices - currently disabled
dotenv.load_dotenv()
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

def get_token_price_usd(symbol, convert_to_symbol="USD"):
    # ... implementation details ...
    pass
'''

# ------------------------ Global Variables ------------------------
G = nx.DiGraph()

# ------------------------ Route Calculation Function ------------------------
def calculate_routes(G: nx.DiGraph(), paths: list, sell_amount: float, sell_ID: str, buy_ID: str) -> dict:

    gas_fee = 9.022557516e-06
    count = 0 # Counter for generating unique route keys
    routes = []

    for path in paths:
        try:
            swap_number = 0
            output_amount = 0.0
            output_symbol = ""

            # Iterate through each pool (swap step) in the current path
            for pool_id in path:

                pool_data = G.nodes[pool_id]['pool']
                protocol = pool_data['protocol']
                dangerous = pool_data.get('dangerous', False) # Check if pool is marked dangerous

                # ------------------------ Process First Swap in the Path ------------------------
                if pool_id == path[0]:
                    current_route = {
                        "amount_in": 0,
                        "amount_in_usd": 0,
                        "amount_out": 0,
                        "amount_out_usd": 0,
                        "gas_fee": 0,
                        "path": path,
                        "rate_exchange": 0,
                        "rate_receive": 0,
                        "swap": []
                    }
                    current_input_amount = sell_amount
                    current_input_ID = sell_ID

                    input_index = 0
                    if 'token1' in pool_data and current_input_ID == pool_data['token1']['id']:
                        input_index = 1 
                    output_index = input_index^1
                    output_symbol = pool_data[f'token{output_index}']['symbol']
                    current_input_symbol = pool_data[f'token{input_index}']['symbol']

                    # TODO: price_impact(spot price)
                    output_amount = simulateSwap(
                        pool_data, current_input_amount, input_index, output_index)
                    if output_amount == 0:
                        print(f"output_amount is 0, pool_id: {pool_id}")

                    # ------------------------ Store First Swap Details ------------------------
                    # Initialize the route entry in the routes dictionary
                    current_route["swap"].append({
                        'pool': pool_id,
                        'exchange': protocol,
                        'dangerous': dangerous,
                        'input_token': current_input_symbol,
                        'input_amount': current_input_amount,
                        'input_amount_usd': current_input_amount * float(pool_data[f'token{input_index}']['priceUSD']) if f'token{input_index}' in pool_data and 'priceUSD' in pool_data[f'token{input_index}'] else 0,
                        'output_token': output_symbol,
                        'output_amount': output_amount,
                        'output_amount_usd': output_amount * float(pool_data[f'token{output_index}']['priceUSD']) if f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else 0,
                        # TODO: spot price and price_impact
                        'execute_price': output_amount / current_input_amount,
                        'gas_fee': gas_fee, # Gas fee estimate per swap
                    })
                    swap_number += 1

                # ------------------------ Process Subsequent Swaps in the Path ------------------------
                else:
                    # Input for this swap is the output from the previous swap
                    current_input_amount = output_amount
                    current_input_symbol = output_symbol

                    input_index = 0
                    if 'token1' in pool_data and current_input_symbol == pool_data['token1']['symbol']:
                        input_index = 1 
                    output_index = input_index^1
                    output_symbol = pool_data[f'token{output_index}']['symbol']

                    # TODO: price_impact(spot price)
                    output_amount = simulateSwap(
                        pool_data, current_input_amount, input_index, output_index)

                    # ------------------------ Store Intermediate Swap Details ------------------------
                    current_route["swap"].append({
                        'pool': pool_id,
                        'exchange': protocol,
                        'dangerous': dangerous,
                        'input_token': current_input_symbol,
                        'input_amount': current_input_amount,
                        'input_amount_usd': current_input_amount * float(pool_data[f'token{input_index}']['priceUSD']) if f'token{input_index}' in pool_data and 'priceUSD' in pool_data[f'token{input_index}'] else 0,
                        'output_token': output_symbol,
                        'output_amount': output_amount,
                        'output_amount_usd': output_amount * float(pool_data[f'token{output_index}']['priceUSD']) if f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else 0,
                        # 'spot price':
                        'execute_price': output_amount / current_input_amount,
                        'gas_fee': gas_fee, # Gas fee estimate per swap
                    })
                    swap_number += 1

            # ------------------------ Store overall route summary information ------------------------

            else: # This 'else' block executes when the inner loop finishes normally (no break/error)

                amount_in = sell_amount
                amount_in_usd = current_route['swap'][0]['input_amount_usd']
                amount_out = output_amount
                amount_out_usd = current_route['swap'][swap_number - 1]['output_amount_usd']
                rate_exchange = sell_amount / output_amount if output_amount else 0
                rate_receive = amount_out_usd / amount_in_usd if amount_in_usd else 0

                total_gas_fee = gas_fee * swap_number

                # === Step 2: 分别赋值并转为字符串 ===
                current_route['amount_in'] = str(amount_in)
                current_route['amount_in_usd'] = str(amount_in_usd)
                current_route['amount_out'] = str(amount_out)
                current_route['amount_out_usd'] = str(amount_out_usd)
                current_route['rate_exchange'] = str(rate_exchange)
                current_route['rate_receive'] = str(rate_receive)
                current_route['gas_fee'] = str(total_gas_fee)
                current_route['path'] = path
                # TODO: spot price and price_impact
                routes.append(current_route)
                swap_number = 0
                count += 1

        # ------------------------ Error Handling for Path Calculation ------------------------
        except Exception as e:
            # If an error occurred during calculation for this path, remove its entry if partially created
            if f'route_{count}' in routes:
                del routes[f'route_{count}']
            # Print the error and continue to the next path
            print(f"Error processing path {path}: {e}")
            import traceback
            traceback.print_exc() # Print stack trace for debugging
            continue # Go to the next path in the outer loop

    # ------------------------ Sort Routes ------------------------
    # After processing all paths, sort the resulting routes dictionary by final 'amount_out' descending
    # Converts dict to list of tuples: [(route_key, route_data), ...]
    sorted_routes = sorted(routes, key=lambda item: item.get('amount_out', 0), reverse=True) # Use .get for safety

    return sorted_routes

# ------------------------ Sub-Route Calculation Function (for Trade Splitting) ------------------------
def get_sub_route(g: nx.DiGraph(), path: list, new_sell_amount: float, sell_symbol: str, p: float, gas_fee: float) -> dict:
    """
    Calculates the details of a single path for a specific input amount (part of a split trade).
    This function is very similar to the inner loop of `calculate_routes`, but operates on a single path
    and a potentially smaller `new_sell_amount`.

    Args:
        g (nx.DiGraph): The graph containing pool data.
        path (list): The list of pool IDs for this specific path.
        new_sell_amount (float): The portion of the original sell amount allocated to this sub-route.
        sell_symbol (str): The symbol of the token being sold.
        p (float): The percentage of the original total amount this sub-route represents.
        gas_fee (float): The estimated gas fee per swap (passed from caller).

    Returns:
        dict: A dictionary containing the detailed steps and results for this sub-route,
              including the percentage 'p'. Returns an empty dict or raises error on failure.
    """
    route = {'percent': p} # Initialize the result dictionary with the percentage
    swap_no = 0
    output_amount = 0.0 # Initialize output amount
    output_symbol = "" # Initialize output symbol

    # Iterate through each pool (swap step) in the path
    for pool_id in path:
        # Retrieve pool data
        pool_data = g.nodes[pool_id]['pool']
        protocol = pool_data['protocol']
        dangerous = pool_data.get('dangerous', False)

        # ------------------------ Select Price Impact Function ------------------------
        if protocol == 'Balancer_V1' or protocol == 'Balancer_V2':
            price_impact_function = constant_mean_price_impact
        elif protocol == 'DODO':
            price_impact_function = dodo_price_impact
        # Add elif for CURVE, V3 etc. if integrated
        else:
            price_impact_function = xyk_price_impact

        # ------------------------ Process First Swap ------------------------
        if pool_id == path[0]:
            current_input_amount = new_sell_amount # Use the allocated amount for this sub-route
            current_input_symbol = sell_symbol

            values = price_impact_function(
                pool_data, current_input_symbol, current_input_amount)

            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']

            if output_amount is None or price_impact == float('inf'):
                raise ValueError(f"Sub-route calculation failed at first swap ({pool_id}): {values.get('description', 'Calculation error')}")

            output_index = 0
            if 'token1' in pool_data and output_symbol == pool_data['token1']['symbol']:
                output_index = 1

            output_amount_zero = abs(output_amount) < 1e-12

            # ------------------------ Store First Swap Details ------------------------
            route[f'swap_{swap_no}'] = {
                'pool': pool_id,
                'exchange': protocol,
                'dangerous': dangerous,
                'input_token': current_input_symbol,
                'input_amount': current_input_amount,
                'input_amount_usd': current_input_amount * float(pool_data[f'token{output_index^1}']['priceUSD']) if not output_amount_zero and f'token{output_index^1}' in pool_data and 'priceUSD' in pool_data[f'token{output_index^1}'] else 0,
                'output_token': output_symbol,
                'output_amount': output_amount,
                'output_amount_usd': output_amount * float(pool_data[f'token{output_index}']['priceUSD']) if not output_amount_zero and f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else 0,
                'price_impact': price_impact,
                'price': current_input_amount / output_amount if not output_amount_zero else float('inf'),
                'price_usd': (current_input_amount * float(pool_data[f'token{output_index^1}']['priceUSD'])) / (output_amount * float(pool_data[f'token{output_index}']['priceUSD'])) if not output_amount_zero and f'token{output_index^1}' in pool_data and 'priceUSD' in pool_data[f'token{output_index^1}'] and f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else float('inf'),
                'gas_fee': gas_fee, # Use the passed gas_fee estimate
                'description': description,
            }

        # ------------------------ Process Subsequent Swaps ------------------------
        else:
            current_input_amount = output_amount
            current_input_symbol = output_symbol

            if abs(current_input_amount) < 1e-12:
                 raise ValueError(f"Sub-route calculation broken at swap {swap_no} ({pool_id}): Zero input amount.")

            values = price_impact_function(
                pool_data, current_input_symbol, current_input_amount)

            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']

            if output_amount is None or price_impact == float('inf'):
                 raise ValueError(f"Sub-route calculation failed at swap {swap_no} ({pool_id}): {values.get('description', 'Calculation error')}")

            output_index = 0
            if 'token1' in pool_data and output_symbol == pool_data['token1']['symbol']:
                output_index = 1

            output_amount_zero = abs(output_amount) < 1e-12

            # ------------------------ Store Intermediate Swap Details ------------------------
            route[f'swap_{swap_no}'] = {
                'pool': pool_id,
                'exchange': protocol,
                'dangerous': dangerous,
                'input_token': current_input_symbol,
                'input_amount': current_input_amount,
                'input_amount_usd': current_input_amount * float(pool_data[f'token{output_index^1}']['priceUSD']) if not output_amount_zero and f'token{output_index^1}' in pool_data and 'priceUSD' in pool_data[f'token{output_index^1}'] else 0,
                'output_token': output_symbol,
                'output_amount': output_amount,
                'output_amount_usd': output_amount * float(pool_data[f'token{output_index}']['priceUSD']) if not output_amount_zero and f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else 0,
                'price_impact': price_impact,
                'price': current_input_amount / output_amount if not output_amount_zero else float('inf'),
                'price_usd': (current_input_amount * float(pool_data[f'token{output_index^1}']['priceUSD'])) / (output_amount * float(pool_data[f'token{output_index}']['priceUSD'])) if not output_amount_zero and f'token{output_index^1}' in pool_data and 'priceUSD' in pool_data[f'token{output_index^1}'] and f'token{output_index}' in pool_data and 'priceUSD' in pool_data[f'token{output_index}'] else float('inf'),
                'gas_fee': gas_fee,
                'description': description,
                # 'percent': p # Percentage is added at the root level of the dict
            }
        swap_no += 1

    # The loop finishes, return the dictionary containing all swap steps for this sub-route
    return route


# ------------------------ Final Route Aggregation and Splitting Function ------------------------
def get_final_route(g: nx.DiGraph(), routes: list, sell_amount: float, sell_symbol: str) -> dict:
    """
    Determines the final execution strategy, potentially splitting the trade
    across multiple paths to minimize overall price impact based on calculated limits.

    Args:
        g (nx.DiGraph): The graph containing pool data.
        routes (list): A list of sorted route tuples `(route_key, route_data)` from `calculate_routes`.
        sell_amount (float): The total amount of the token to sell.
        sell_symbol (str): The symbol of the token being sold.

    Returns:
        dict: A dictionary representing the final route execution plan.
              Contains a 'paths' list where each element is a sub-route dictionary
              (from `get_sub_route`) representing a portion of the trade.
              Also includes aggregated 'output_amount', 'output_amount_usd', 'gas_fee',
              'price', 'price_usd', and averaged 'price_impact'.
    """
    final_route = {'paths': []} # Initialize the result structure
    remaining = sell_amount     # Amount left to allocate across paths
    gas_fee = get_gas_fee_in_eth() # Get a single gas estimate (used for all sub-routes)
    route_num = 0               # Counter for the number of paths used in the split

    # Iterate through the routes sorted by best output amount first
    for _, route_data in routes: # route_data is the dictionary calculated by calculate_routes

        # ------------------------ Determine Max Amount for this Path ------------------------
        # Call get_max_amount_for_impact_limit to find how much can be sent
        # through this path without exceeding the price impact threshold in any single step.
        # Note: get_max_amount_for_impact_limit expects a specific 'route' format
        #       containing swap dicts directly under the key, matching route_data's structure.
        max_allowed_for_path = get_max_amount_for_impact_limit(g, route_data) # Pass the route_data dictionary

        # Determine the amount to actually send: minimum of the allowed amount and the remaining total amount
        amount_for_this_path = min(max_allowed_for_path, remaining)

        # Calculate the percentage this amount represents of the original total
        p = (amount_for_this_path / sell_amount) * 100

        # ------------------------ Check if Percentage is Significant ------------------------
        # Skip paths that would handle less than 1% of the total trade (configurable threshold)
        if p < 1:
            continue

        # ------------------------ Add Sub-Route to Final Plan ------------------------
        # Calculate the details for this specific path segment using the allocated amount
        try:
            sub_route_details = get_sub_route(
                g, route_data['path'], amount_for_this_path, sell_symbol, p, gas_fee)
            final_route['paths'].append(sub_route_details)
            route_num += 1 # Increment count of used paths
        except Exception as e:
             print(f"Error calculating sub-route for path {route_data['path']}: {e}")
             continue # Skip this path if sub-route calculation fails


        # ------------------------ Update Remaining Amount ------------------------
        remaining -= amount_for_this_path

        # ------------------------ Check Termination Conditions ------------------------
        # Stop if the maximum number of routes (MAX_ROUTES) for splitting is reached
        if route_num >= MAX_ROUTES:
            print(f"Reached MAX_ROUTES limit ({MAX_ROUTES}).")
            break
        # Stop if the remaining amount is negligible
        if remaining < 0.01: # Use a small threshold to handle floating point inaccuracies
             print("Remaining amount negligible, stopping split.")
             break

    # ------------------------ Aggregate Results from Split Paths ------------------------
    # Ensure 'paths' list is not empty before proceeding
    if not final_route['paths']:
        print("Warning: No valid paths found or calculated for the final route.")
        return { # Return an empty/error structure
             'paths': [], 'output_amount': 0, 'output_amount_usd': 0, 'gas_fee': 0,
             'price': float('inf'), 'price_usd': float('inf'), 'price_impact': float('inf')
        }
        
    # Sum the output amounts from the last swap of each sub-route path
    total_output_amount = 0
    total_output_amount_usd = 0
    total_gas_fee = 0
    total_price_impact_weighted = 0 # For averaging later
    num_swaps_total = 0 # Count total swaps for averaging price impact

    for sub_route in final_route['paths']:
        # Find the last swap key (e.g., 'swap_0', 'swap_1', ...)
        # Assumes keys are 'percent', 'swap_0', 'swap_1', ...
        last_swap_index = -1
        for k in sub_route.keys():
            if k.startswith('swap_'):
                try:
                    last_swap_index = max(last_swap_index, int(k.split('_')[1]))
                except (ValueError, IndexError):
                    pass # Ignore keys that don't fit the pattern

        if last_swap_index != -1:
             last_swap_key = f'swap_{last_swap_index}'
             if last_swap_key in sub_route:
                 total_output_amount += sub_route[last_swap_key].get('output_amount', 0)
                 total_output_amount_usd += sub_route[last_swap_key].get('output_amount_usd', 0)
                 # Sum gas fees for all swaps in this sub_route
                 num_swaps_in_subroute = last_swap_index + 1
                 total_gas_fee += sub_route[last_swap_key].get('gas_fee', 0) * num_swaps_in_subroute # Assumes gas_fee is per swap
                 num_swaps_total += num_swaps_in_subroute
                 # Calculate weighted price impact sum (impact * percentage)
                 # Get total impact for this sub-route
                 sub_route_total_impact = sum(sub_route[f'swap_{i}'].get('price_impact', 0) for i in range(num_swaps_in_subroute))
                 total_price_impact_weighted += sub_route_total_impact * (sub_route.get('percent', 0) / 100.0)


    final_route['output_amount'] = total_output_amount
    final_route['output_amount_usd'] = total_output_amount_usd
    final_route['gas_fee'] = total_gas_fee # Total estimated gas for all swaps in the split

    # ------------------------ Calculate Aggregated Price and Price Impact ------------------------
    # Handle potential division by zero if total output is zero
    k = 1e-12 # Small number to avoid true zero division
    final_route['price'] = sell_amount / (final_route['output_amount'] + k) if final_route['output_amount'] is not None else float('inf')
    final_route['price_usd'] = final_route.get('amount_in_usd', sell_amount) / (final_route['output_amount_usd'] + k) if final_route['output_amount_usd'] is not None else float('inf') # Need amount_in_usd

    """     
    Calculate average price impact across splits (weighted by percentage maybe?)
    Simple average across swaps:
    final_route['price_impact'] = total_price_impact_sum / num_swaps_total if num_swaps_total > 0 else 0
    Weighted average based on path percentage (more representative):
    The variable total_price_impact_weighted already holds the sum(path_impact * path_percentage/100)
    However, path_impact was calculated as sum(swap_impacts). This needs review.
    A simpler average: Average of the final price impact reported by each sub-route?
    Current code seems flawed: sums impacts and divides by (len(final_route) - 3)? This is likely wrong.
    Let's calculate a simple average of the *total* price impact of each used path, weighted by percentage. 
    """
    avg_price_impact = 0
    if sell_amount > 0 and len(final_route['paths']) > 0:
       weighted_impact_sum = 0
       for sub_route in final_route['paths']:
           # Recalculate total impact for the sub_route
           sub_route_total_impact = 0
           sub_route_swaps = 0
           for k, v in sub_route.items():
                if k.startswith('swap_'):
                    sub_route_total_impact += v.get('price_impact', 0)
                    sub_route_swaps += 1
           # Weighted sum: (path_impact * path_percentage / 100)
           weighted_impact_sum += sub_route_total_impact * (sub_route.get('percent', 0) / 100.0)
       avg_price_impact = weighted_impact_sum # Weighted average impact

    final_route['price_impact'] = avg_price_impact # Store the calculated average impact

    return final_route