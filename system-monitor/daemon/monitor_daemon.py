# daemon/monitor_daemon.py
import asyncio
import json
import socket
import struct
import logging
import websockets
from datetime import datetime
from typing import Set, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MonitorDaemon')

class SystemMonitorDaemon:
    NETLINK_USER = 31
    MAX_PROCESSES = 100
    NR_CPUS = 8  # Adjust based on your system

    def __init__(self, websocket_port: int = 8765):
        self.websocket_port = websocket_port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.metrics_history: Dict[str, list] = {
            'cpu': [],
            'memory': [],
            'timestamp': []
        }
        self.max_history_size = 300  # 5 minutes of data at 1-second intervals
        self.setup_netlink_socket()

    def setup_netlink_socket(self) -> None:
        """Initialize Netlink socket for kernel communication"""
        try:
            self.sock = socket.socket(socket.AF_NETLINK, 
                                    socket.SOCK_RAW, 
                                    self.NETLINK_USER)
            self.sock.bind((0, 0))  # Bind to all groups
            self.sock.setblocking(False)
            logger.info("Netlink socket initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Netlink socket: {e}")
            raise

    def parse_metrics(self, data: bytes) -> Dict[str, Any]:
        """Parse binary metrics data from kernel"""
        try:
            # Define format string based on kernel structure
            fmt = (f'{self.NR_CPUS}Q'  # cpu_usage array
                  'QQQQQ'              # memory stats
                  f'{self.MAX_PROCESSES}(iQ64sQI)'  # process_info array
                  'iQ')                # process_count and timestamp

            # Unpack binary data
            unpacked = struct.unpack(fmt, data)
            
            # Extract CPU usage
            cpu_usage = list(unpacked[:self.NR_CPUS])
            offset = self.NR_CPUS

            # Extract memory information
            memory = {
                'total': unpacked[offset],
                'used': unpacked[offset + 1],
                'free': unpacked[offset + 2],
                'cached': unpacked[offset + 3],
                'available': unpacked[offset + 4]
            }
            offset += 5

            # Extract process information
            processes = []
            process_count = unpacked[-2]
            for i in range(process_count):
                idx = offset + (i * 5)  # 5 values per process
                processes.append({
                    'pid': unpacked[idx],
                    'cpu_usage': unpacked[idx + 1],
                    'name': unpacked[idx + 2].decode().strip('\x00'),
                    'memory_usage': unpacked[idx + 3],
                    'state': unpacked[idx + 4]
                })

            # Create metrics dictionary
            metrics = {
                'cpu_usage': cpu_usage,
                'cpu_average': sum(cpu_usage) / len(cpu_usage),
                'memory': memory,
                'processes': processes,
                'timestamp': datetime.fromtimestamp(unpacked[-1]).isoformat()
            }

            # Update history
            self.update_metrics_history(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error parsing metrics data: {e}")
            return {}

    def update_metrics_history(self, metrics: Dict[str, Any]) -> None:
        """Update metrics history with new data"""
        self.metrics_history['cpu'].append(metrics['cpu_average'])
        self.metrics_history['memory'].append(
            metrics['memory']['used'] / metrics['memory']['total'] * 100
        )
        self.metrics_history['timestamp'].append(metrics['timestamp'])

        # Maintain history size
        if len(self.metrics_history['cpu']) > self.max_history_size:
            self.metrics_history['cpu'].pop(0)
            self.metrics_history['memory'].pop(0)
            self.metrics_history['timestamp'].pop(0)

    async def broadcast_metrics(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all connected WebSocket clients"""
        if not self.clients:
            return

        # Add history to metrics
        metrics['history'] = self.metrics_history
        
        # Prepare message
        message = json.dumps(metrics)
        
        # Broadcast to all clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.clients -= disconnected_clients

    async def handle_netlink(self) -> None:
        """Handle Netlink socket communication"""
        while True:
            try:
                # Wait for data from kernel
                data = await asyncio.get_event_loop().sock_recv(
                    self.sock, 65536)
                
                if data:
                    # Skip netlink header (16 bytes)
                    metrics = self.parse_metrics(data[16:])
                    if metrics:
                        await self.broadcast_metrics(metrics)
                        
            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error handling netlink data: {e}")
                await asyncio.sleep(1)

    async def register_client(self, 
                            websocket: websockets.WebSocketServerProtocol) -> None:
        """Register new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"New client connected. Total clients: {len(self.clients)}")
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            logger.info(
                f"Client disconnected. Total clients: {len(self.clients)}")

    async def start_server(self) -> None:
        """Start WebSocket server and Netlink handler"""
        async with websockets.serve(
            self.register_client, 
            "localhost", 
            self.websocket_port
        ):
            logger.info(f"WebSocket server started on port {self.websocket_port}")
            await self.handle_netlink()

    def run(self) -> None:
        """Run the daemon"""
        try:
            asyncio.get_event_loop().run_until_complete(self.start_server())
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down daemon...")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
        finally:
            self.sock.close()

if __name__ == "__main__":
    try:
        daemon = SystemMonitorDaemon()
        daemon.run()
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}")