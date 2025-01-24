# ui/tui/monitor_tui.py
import asyncio
import curses
import json
import websockets
import signal
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque

class MonitorTUI:
    def __init__(self):
        # Initialize color pairs
        self.COLOR_PAIRS = {
            'header': 1,
            'normal': 2,
            'highlight': 3,
            'cpu_normal': 4,
            'cpu_high': 5,
            'memory_normal': 6,
            'memory_high': 7,
            'graph': 8
        }
        
        # Initialize data structures
        self.cpu_history: deque = deque(maxlen=100)
        self.memory_history: deque = deque(maxlen=100)
        self.current_metrics: Dict[str, Any] = {}
        self.sort_by: str = 'cpu_usage'
        self.sort_reverse: bool = True
        self.selected_row: int = 0
        self.scroll_offset: int = 0
        
        # Initialize curses
        self.screen = curses.initscr()
        self.setup_curses()

    def setup_curses(self) -> None:
        """Initialize curses settings"""
        curses.start_color()
        curses.use_default_colors()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(1)
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)
        curses.init_pair(8, curses.COLOR_YELLOW, -1)

    def draw_header(self) -> None:
        """Draw the header bar"""
        header = f" System Monitor - Press 'q' to quit | Sort: {self.sort_by} "
        self.screen.addstr(0, 0, header.ljust(curses.COLS), 
                          curses.color_pair(self.COLOR_PAIRS['header']))

    def draw_cpu_usage(self, y_pos: int) -> int:
        """Draw CPU usage information"""
        if 'cpu_usage' not in self.current_metrics:
            return y_pos

        cpu_data = self.current_metrics['cpu_usage']
        self.screen.addstr(y_pos, 0, "CPU Usage:", 
                          curses.color_pair(self.COLOR_PAIRS['normal']))
        y_pos += 1

        for i, usage in enumerate(cpu_data):
            usage_percent = min(100, max(0, usage))
            color = (self.COLOR_PAIRS['cpu_high'] if usage_percent > 80 
                    else self.COLOR_PAIRS['cpu_normal'])
            bar_width = int((curses.COLS - 20) * usage_percent / 100)
            bar = f"CPU{i:2d} [{('|' * bar_width).ljust(curses.COLS - 20)}] {usage_percent:5.1f}%"
            self.screen.addstr(y_pos + i, 0, bar, curses.color_pair(color))

        return y_pos + len(cpu_data) + 1

    def draw_memory_usage(self, y_pos: int) -> int:
        """Draw memory usage information"""
        if 'memory' not in self.current_metrics:
            return y_pos

        mem = self.current_metrics['memory']
        total_gb = mem['total'] / (1024 ** 3)
        used_gb = mem['used'] / (1024 ** 3)
        usage_percent = (mem['used'] / mem['total']) * 100

        color = (self.COLOR_PAIRS['memory_high'] if usage_percent > 80 
                else self.COLOR_PAIRS['memory_normal'])
        bar_width = int((curses.COLS - 20) * usage_percent / 100)
        
        self.screen.addstr(y_pos, 0, "Memory Usage:", 
                          curses.color_pair(self.COLOR_PAIRS['normal']))
        bar = f"[{('|' * bar_width).ljust(curses.COLS - 20)}] {usage_percent:5.1f}%"
        self.screen.addstr(y_pos + 1, 0, bar, curses.color_pair(color))
        
        details = f"Total: {total_gb:.1f}GB | Used: {used_gb:.1f}GB"
        self.screen.addstr(y_pos + 2, 0, details, 
                          curses.color_pair(self.COLOR_PAIRS['normal']))

        return y_pos + 4

    def draw_process_list(self, y_pos: int) -> None:
        """Draw the process list"""
        if 'processes' not in self.current_metrics:
            return

        # Header
        header = " PID    CPU%   MEM%   STATE   NAME"
        self.screen.addstr(y_pos, 0, header, 
                          curses.color_pair(self.COLOR_PAIRS['header']))
        y_pos += 1

        # Sort processes
        processes = sorted(
            self.current_metrics['processes'],
            key=lambda x: x[self.sort_by],
            reverse=self.sort_reverse
        )

        # Calculate visible rows
        visible_rows = curses.LINES - y_pos - 1
        start_idx = self.scroll_offset
        end_idx = min(start_idx + visible_rows, len(processes))

        # Draw processes
        for i, proc in enumerate(processes[start_idx:end_idx], start=start_idx):
            color = (self.COLOR_PAIRS['highlight'] 
                    if i == self.selected_row 
                    else self.COLOR_PAIRS['normal'])
            
            line = f" {proc['pid']:5d}  {proc['cpu_usage']:5.1f}  {proc['memory_usage']:5.1f}  {proc['state']:6s}  {proc['name']}"
            self.screen.addstr(y_pos + i - start_idx, 0, 
                             line.ljust(curses.COLS), 
                             curses.color_pair(color))

    def draw_graphs(self) -> None:
        """Draw CPU and memory history graphs"""
        if not self.cpu_history or not self.memory_history:
            return

        graph_width = curses.COLS // 4
        graph_height = 10

        # Draw CPU history graph
        self.screen.addstr(2, curses.COLS - graph_width - 2, 
                          "CPU History", 
                          curses.color_pair(self.COLOR_PAIRS['graph']))
        self.draw_graph(self.cpu_history, 3, curses.COLS - graph_width - 2, 
                       graph_width, graph_height)

        # Draw memory history graph
        self.screen.addstr(graph_height + 4, curses.COLS - graph_width - 2, 
                          "Memory History", 
                          curses.color_pair(self.COLOR_PAIRS['graph']))
        self.draw_graph(self.memory_history, graph_height + 5, 
                       curses.COLS - graph_width - 2, 
                       graph_width, graph_height)

    def draw_graph(self, data: deque, y: int, x: int, 
                  width: int, height: int) -> None:
        """Draw a single graph"""
        if not data:
            return

        max_val = max(data)
        min_val = min(data)
        range_val = max_val - min_val or 1

        for i in range(height):
            self.screen.addstr(y + i, x, '|', 
                             curses.color_pair(self.COLOR_PAIRS['graph']))
            
        for i, value in enumerate(list(data)[-width:]):
            graph_height = int((value - min_val) * (height - 1) / range_val)
            self.screen.addstr(y + height - 1 - graph_height, x + i + 1, '•', 
                             curses.color_pair(self.COLOR_PAIRS['graph']))

    async def handle_input(self) -> bool:
        """Handle user input"""
        try:
            self.screen.nodelay(1)
            key = self.screen.getch()
            
            if key == ord('q'):
                return False
            elif key == ord('c'):
                self.sort_by = 'cpu_usage'
                self.sort_reverse = True
            elif key == ord('m'):
                self.sort_by = 'memory_usage'
                self.sort_reverse = True
            elif key == curses.KEY_UP:
                self.selected_row = max(0, self.selected_row - 1)
                if self.selected_row < self.scroll_offset:
                    self.scroll_offset = self.selected_row
            elif key == curses.KEY_DOWN:
                self.selected_row = min(len(self.current_metrics['processes']) - 1, 
                                      self.selected_row + 1)
                if self.selected_row >= self.scroll_offset + curses.LINES - 6:
                    self.scroll_offset = self.selected_row - curses.LINES + 7

            return True
        except Exception:
            return True

    async def update_display(self) -> None:
        """Update the display with current metrics"""
        try:
            self.screen.clear()
            self.draw_header()
            y_pos = 1
            y_pos = self.draw_cpu_usage(y_pos)
            y_pos = self.draw_memory_usage(y_pos)
            self.draw_process_list(y_pos)
            self.draw_graphs()
            self.screen.refresh()
        except Exception as e:
            self.screen.addstr(0, 0, f"Error updating display: {str(e)}")
            self.screen.refresh()

    async def run(self) -> None:
        """Main run loop"""
        try:
            async with websockets.connect('ws://localhost:8765') as websocket:
                while True:
                    try:
                        # Handle WebSocket message
                        message = await websocket.recv()
                        self.current_metrics = json.loads(message)
                        
                        # Update history
                        if 'cpu_usage' in self.current_metrics:
                            self.cpu_history.append(
                                sum(self.current_metrics['cpu_usage']) / 
                                len(self.current_metrics['cpu_usage'])
                            )
                        if 'memory' in self.current_metrics:
                            self.memory_history.append(
                                self.current_metrics['memory']['used'] / 
                                self.current_metrics['memory']['total'] * 100
                            )
                        
                        # Update display
                        await self.update_display()
                        
                        # Handle input
                        if not await self.handle_input():
                            break
                            
                    except websockets.exceptions.ConnectionClosed:
                        self.screen.addstr(0, 0, "Connection lost. Retrying...")
                        self.screen.refresh()
                        await asyncio.sleep(1)
                        break
                    except Exception as e:
                        self.screen.addstr(0, 0, f"Error: {str(e)}")
                        self.screen.refresh()
                        await asyncio.sleep(1)

        finally:
            curses.endwin()

def main():
    # Handle SIGINT gracefully
    signal.signal(signal.SIGINT, lambda x, y: None)
    
    # Run the TUI
    tui = MonitorTUI()
    asyncio.get_event_loop().run_until_complete(tui.run())

if __name__ == "__main__":
    main()