from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
import asyncio
import threading
from smart_order_router import route_orders, refresh_pools
from constants import DEX_LIST

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------------------------- Swagger UI settings ----------------------------
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Smart Order Router"}
)
app.register_blueprint(swaggerui_blueprint)

# ---------------------------- background refresh task ----------------------------
def background_refresh_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def refresh_loop():
        while True:
            print("🔁 auto refreshing pools...")
            await asyncio.gather(*(refresh_pools(dex) for dex in DEX_LIST))
            await asyncio.sleep(3000)
    
    loop.run_until_complete(refresh_loop())

# Start background refresh in a separate thread
refresh_thread = threading.Thread(target=background_refresh_task, daemon=True)
refresh_thread.start()

# ---------------------------- route interface ----------------------------

@app.route('/', methods=['GET'])
def index():
    return redirect('/api/docs')

@app.route('/DEX_LIST', methods=['GET'])
def get_dex_list():
    return jsonify(DEX_LIST)

# http://127.0.0.1:5000/order_router?sell_ID=0xdAC17F958D2ee523a2206206994597C13D831ec7&sell_amount=1000&buy_ID=0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2&exchanges=Uniswap_V2,Sushiswap_V2
@app.route('/order_router', methods=['GET'])
def order_router():
    sell_ID = request.args.get('sell_ID')
    sell_amount = float(request.args.get('sell_amount', 0))
    buy_ID = request.args.get('buy_ID')
    exchanges = request.args.get('exchanges', '').split(',') if request.args.get('exchanges') else DEX_LIST

    # Create a new event loop for this request
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(route_orders(sell_ID, sell_amount, buy_ID, exchanges, 20, split=False))
    loop.close()
    
    return jsonify(result)

@app.route('/refresh_pools', methods=['GET'])
def refresh_pools_route():
    # Create a new event loop for this request
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(*(refresh_pools(dex) for dex in DEX_LIST)))
    loop.close()
    
    return jsonify({'status': 'refreshed'})

# ---------------------------- start the server ----------------------------

if __name__ == '__main__':
    import os
    os.environ["FLASK_ENV"] = "development"
    app.run(debug=True)