#!/usr/bin/env python3

import asyncio
import json
import socket
import struct
import logging
import websockets
from datetime import datetime
from typing import Set, Dict, Any
import ctypes
from pathlib import Path
import signal
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('system_monitor.log')
    ]
)
logger = logging.getLogger('SystemMonitor')

# Constants matching kernel module
NETLINK_TEST = 31
MAX_PROCESSES = 100
NR_CPUS = 32
TASK_COMM_LEN = 16

class ProcessInfo(ctypes.Structure):
    """Process information structure matching kernel module"""
    _pack_ = 1
    _fields_ = [
        ('pid', ctypes.c_int),
        ('cpu_usage', ctypes.c_ulong),
        ('comm', ctypes.c_char * TASK_COMM_LEN),
        ('mem_usage', ctypes.c_ulong),
        ('state', ctypes.c_long),
        ('priority', ctypes.c_ulong),
        ('nice', ctypes.c_ulong)
    ]

class MemoryInfo(ctypes.Structure):
    """Memory information structure matching kernel module"""
    _pack_ = 1
    _fields_ = [
        ('total', ctypes.c_ulong),
        ('used', ctypes.c_ulong),
        ('free', ctypes.c_ulong),
        ('cached', ctypes.c_ulong),
        ('available', ctypes.c_ulong),
        ('buffers', ctypes.c_ulong)
    ]

class SystemMetrics(ctypes.Structure):
    """System metrics structure matching kernel module"""
    _pack_ = 1
    _fields_ = [
        ('cpu_usage', ctypes.c_ulong * NR_CPUS),
        ('memory', MemoryInfo),
        ('processes', ProcessInfo * MAX_PROCESSES),
        ('process_count', ctypes.c_int),
        ('timestamp', ctypes.c_ulong)
    ]

class SystemMonitorDaemon:
    """Main daemon class for system monitoring"""

    def __init__(self, websocket_port: int = 8765):
        self.websocket_port = websocket_port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.metrics_history: Dict[str, list] = {
            'cpu': [],
            'memory': [],
            'timestamp': []
        }
        self.max_history_size = 300  # 5 minutes at 1-second intervals
        self.running = True
        self.loop = None
        self.server = None
        self.setup_netlink_socket()
        self.setup_signal_handlers()
        logger.info("Daemon initialized")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, self.handle_shutdown)
        logger.debug("Signal handlers configured")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
        if self.loop and self.loop.is_running():
            self.loop.create_task(self.cleanup())
            self.loop.stop()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients]
            )
            self.clients.clear()

        # Close netlink socket
        if hasattr(self, 'sock'):
            self.sock.close()

        # Close websocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("Cleanup completed")

    def setup_netlink_socket(self) -> None:
        """Initialize Netlink socket for kernel communication"""
        try:
            self.sock = socket.socket(socket.AF_NETLINK, 
                                    socket.SOCK_RAW, 
                                    NETLINK_TEST)
            self.sock.bind((0, 1))  # Use group 1 for multicast
            self.sock.setblocking(False)
            logger.info("Netlink socket initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Netlink socket: {e}")
            raise

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f}PB"

    def format_metrics(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """Format metrics into a dictionary"""
        try:
            # Validate and format timestamp
            try:
                timestamp = datetime.fromtimestamp(metrics.timestamp).isoformat()
            except (ValueError, OSError):
                timestamp = datetime.now().isoformat()
                logger.warning("Invalid timestamp received, using current time")

            formatted = {
                'cpu_usage': [metrics.cpu_usage[i] for i in range(NR_CPUS)],
                'memory': {
                    'total': metrics.memory.total,
                    'used': metrics.memory.used,
                    'free': metrics.memory.free,
                    'cached': metrics.memory.cached,
                    'available': metrics.memory.available,
                    'buffers': metrics.memory.buffers,
                    'total_formatted': self.format_bytes(metrics.memory.total),
                    'used_formatted': self.format_bytes(metrics.memory.used),
                    'free_formatted': self.format_bytes(metrics.memory.free)
                },
                'processes': [],
                'timestamp': timestamp
            }

            # Process information
            for i in range(metrics.process_count):
                proc = metrics.processes[i]
                formatted['processes'].append({
                    'pid': proc.pid,
                    'name': proc.comm.decode('utf-8', 'ignore').strip('\x00'),
                    'cpu_usage': proc.cpu_usage,
                    'mem_usage': proc.mem_usage,
                    'mem_formatted': self.format_bytes(proc.mem_usage),
                    'state': chr(proc.state),
                    'priority': proc.priority,
                    'nice': proc.nice
                })

            # Sort processes by CPU usage
            formatted['processes'].sort(
                key=lambda x: x['cpu_usage'], 
                reverse=True
            )

            # Calculate CPU average
            active_cpus = [x for x in formatted['cpu_usage'] if x > 0]
            formatted['cpu_average'] = (
                sum(active_cpus) / len(active_cpus) if active_cpus else 0
            )

            return formatted
        except Exception as e:
            logger.error(f"Error formatting metrics: {e}", exc_info=True)
            return {}

    def update_metrics_history(self, metrics: Dict[str, Any]) -> None:
        """Update metrics history"""
        try:
            self.metrics_history['cpu'].append(metrics['cpu_average'])
            self.metrics_history['memory'].append(
                metrics['memory']['used'] / metrics['memory']['total'] * 100
            )
            self.metrics_history['timestamp'].append(metrics['timestamp'])

            # Maintain history size
            if len(self.metrics_history['cpu']) > self.max_history_size:
                for key in self.metrics_history:
                    self.metrics_history[key].pop(0)
        except Exception as e:
            logger.error(f"Error updating history: {e}", exc_info=True)

    async def broadcast_metrics(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all connected WebSocket clients"""
        if not self.clients:
            return

        try:
            metrics['history'] = self.metrics_history
            message = json.dumps(metrics)
            
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected.add(client)

            self.clients -= disconnected
            
            if disconnected:
                logger.info(f"Removed {len(disconnected)} disconnected clients")
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}", exc_info=True)

    async def handle_netlink(self) -> None:
        """Handle Netlink socket communication"""
        while self.running:
            try:
                if not self.running:
                    break

                data = await asyncio.get_event_loop().sock_recv(
                    self.sock, 65536)
                
                if data and self.running:
                    logger.debug(f"Received data size: {len(data)} bytes")
                    # Skip netlink header (16 bytes)
                    metrics = SystemMetrics.from_buffer_copy(data[16:])
                    logger.debug(f"Received metrics with timestamp: {metrics.timestamp}")
                    
                    formatted_metrics = self.format_metrics(metrics)
                    if formatted_metrics:
                        self.update_metrics_history(formatted_metrics)
                        await self.broadcast_metrics(formatted_metrics)
                    else:
                        logger.warning("Failed to format metrics")
                    
            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    logger.error(f"Error handling netlink data: {e}", 
                               exc_info=True)
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
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def start_server(self) -> None:
        """Start WebSocket server and Netlink handler"""
        self.server = await websockets.serve(
            self.register_client, 
            "localhost", 
            self.websocket_port
        )
        logger.info(f"WebSocket server started on port {self.websocket_port}")
        await self.handle_netlink()

    def run(self) -> None:
        """Run the daemon"""
        try:
            logger.info("Starting System Monitor Daemon")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            try:
                self.loop.run_until_complete(self.start_server())
                self.loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Received KeyboardInterrupt")
            finally:
                # Run cleanup
                self.loop.run_until_complete(self.cleanup())
                # Close the event loop
                self.loop.close()
                
        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
        finally:
            logger.info("Daemon shutdown complete")

def main():
    """Main entry point"""
    try:
        # Check if running as root
        if os.geteuid() != 0:
            logger.error("This program must be run as root")
            sys.exit(1)

        daemon = SystemMonitorDaemon()
        daemon.run()
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()