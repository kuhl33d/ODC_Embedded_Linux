# tests/test_client.py
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to daemon")
            while True:
                try:
                    data = await websocket.recv()
                    metrics = json.loads(data)
                    print("\nReceived metrics:")
                    print(f"CPU Average: {metrics.get('cpu_average', 0)}%")
                    print(f"Process Count: {len(metrics.get('processes', []))}")
                    print(f"Memory Used: {metrics.get('memory', {}).get('used', 0) / (1024**3):.2f} GB")
                except websockets.exceptions.ConnectionClosed:
                    print("\nConnection closed by server")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    break
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(test_connection())
    except KeyboardInterrupt:
        print("\nExiting...")