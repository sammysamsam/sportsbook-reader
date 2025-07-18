import json
from playwright.async_api import async_playwright
import asyncio

GAMES = {}
MARKETS = {}

def handle_ws_response(payload):
    payload = json.loads(payload)
    print(payload)
    r = handle_new_markets(payload)
    if r: 
        return 
    
    r = handle_update_markets(payload)
    if r: 
        return 
    
def handle_update_markets(payload):
    if 'Market' in payload:
        market_update = payload['Market']
        market_id = market_update.get('id')
        market_curr = MARKETS.get(market_id)
        if not market_curr:
            print('not found market to update')
            return False
        
        state = market_update.get('state')
        market_curr['state'] = state
        
        selections = market_update.get('selections',[])
        for selection in selections:
            selection_id = selection.get('id')
            selection_curr = market_curr.get(selection_id)
            if selection_curr is None:
                print('not found selection to update')
                return False
                
            # print(selection_curr['name'], selection)
            idx = selection.get('rootIdx')

            if idx is not None:
                selection_curr['idx'] = idx
                selection_curr['state'] = state
        # pprint(MARKETS)
        return True
            # selection_name = selection.get('name')
            # selection_odds = selection.get('odds')
            # if market_id and selection_id and selection_name and selection_odds:
            #     MARKETS[market_id][selection_id] = {
            #         'selection_name': selection_name,
            #     }
    return False
def handle_new_markets(payload):
    if 'SubscriptionResponse' in payload:
        data = payload['SubscriptionResponse'].get('data')
        if not data:
            return True
        id_ = data.get('id')
        name = data.get('name')
        state = data.get('state')
        sport = data.get('sport')
        inplay = data.get('inplay')
        markets = data.get('markets',[])

        if id_ and name:
            GAMES[id_] = {
                'name': name,
                'state': state,
                'sport': sport,
                'inplay': inplay,
                'metadata': data
            }
        for market in markets:
            market_id = market.get('id')
            selections = market.get('selections',[])
            if market_id not in MARKETS:
                MARKETS[market_id] = {}
            MARKETS[market_id] = {
                'displayOdd?':market.get('displayOrder'),
                'game_id': id_,
                'game_name': name,
            
            }
            market_name = market.get('name')
            if market_id and market_name and market_name == 'To Win': 
                for selection in selections:
                    selection_id = selection.get('id')
                    selection_name = selection.get('name')
                    displayOrder = selection.get('displayOrder')
                    
                    if market_id and selection_id and selection_name: 
                        MARKETS[market_id][selection_id] = {
                            'name': selection_name,
                            'displayOrder': displayOrder
                        }
        return True
    return False 

async def monitor(debug_port=9222):
    """Simple script to print POST requests, responses, and WebSocket messages"""

    async with async_playwright() as p:
        try:
            print(f"Connecting to Chrome on port {debug_port}...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")

            default_context = browser.contexts[0]
            pages = default_context.pages

            if not pages:
                print("No pages found in Chrome. Open a page first.")
                return

            page = pages[0]
            print(f"Connected to page: {page.url}")
            print("Listening for requests and WebSocket messages... Press Ctrl+C to stop")

            # Simple request handler
            async def on_request(request):
                url = request.url
                if 'darkly' in url:
                    return
                print(f"\nRequest: {request.method} {request.url}")

            # Simple response handler
            async def on_response(response):
                url = response.url
                if 'darkly' in url:
                    # print('darkly')
                    return
                print('\nResponse: ' + url)
                body = await response.body()
                text = body.decode('utf-8', errors='replace')

                if 'java-graphql/graphql' in response.url:
                    try:
                        payload = json.loads(text)
                        betsync = payload.get('data', {}).get('betSync')
                        print(betsync)
                    except Exception:
                        print(f"\n⚠️ GraphQL Response (undecodable): {text[:200]}")
               
                else:
                    print(f"Response data: {text}\n\n")

            # WebSocket handler
            async def on_websocket(ws):
                print(f"\nWebSocket connected: {ws.url}")

                ws.on("framereceived", lambda payload:
                    handle_ws_response(payload)
                    )
                ws.on("framesent", lambda payload:
                print(f"WS Sent: {payload[:1000]}")
                      )

                ws.on("close", lambda:
                print(f"WebSocket closed: {ws.url}")
                      )

            # Register event listeners
            page.on("request", on_request)
            
            page.on("response", on_response)
            page.on("websocket", on_websocket)

            try:
                # Keep the script running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nMonitoring stopped")
            finally:
                await browser.close()

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    # run this which will serve the network calls first:
    #   sudo "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debugger_profile" https://app.hardrock.bet/home/live
    debug_port = 9222

    async def main():
        task1 = asyncio.create_task(monitor(debug_port))
        await asyncio.gather(task1)

    # Run the main coroutine
    asyncio.run(main())