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
        # Color definitions
        self.COLORS = {
            'header': (curses.COLOR_WHITE, curses.COLOR_BLUE, 1),
            'normal': (curses.COLOR_WHITE, -1, 2),
            'highlight': (curses.COLOR_BLACK, curses.COLOR_WHITE, 3),
            'cpu_low': (curses.COLOR_GREEN, -1, 4),
            'cpu_med': (curses.COLOR_YELLOW, -1, 5),
            'cpu_high': (curses.COLOR_RED, -1, 6),
            'mem_low': (curses.COLOR_GREEN, -1, 7),
            'mem_med': (curses.COLOR_YELLOW, -1, 8),
            'mem_high': (curses.COLOR_RED, -1, 9),
            'graph': (curses.COLOR_CYAN, -1, 10),
            'meter_text': (curses.COLOR_BLUE, -1, 11)
        }
        
        # State variables
        self.current_metrics: Dict[str, Any] = {}
        self.sort_by: str = 'cpu_usage'
        self.sort_reverse: bool = True
        self.selected_row: int = 0
        self.scroll_offset: int = 0
        self.help_visible: bool = False
        self.tree_view: bool = False
        self.show_threads: bool = False
        self.update_interval: float = 1.0
        
        # History tracking
        self.cpu_history: deque = deque(maxlen=100)
        self.memory_history: deque = deque(maxlen=100)
        
        # Initialize curses
        self.screen = curses.initscr()
        self.setup_curses()
        self.init_colors()

    def setup_curses(self) -> None:
        """Initialize curses settings"""
        curses.start_color()
        curses.use_default_colors()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(1)

    def init_colors(self) -> None:
        """Initialize color pairs"""
        for name, (fg, bg, num) in self.COLORS.items():
            curses.init_pair(num, fg, bg)

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}P"

    def draw_meter(self, y: int, x: int, width: int, 
                  percentage: float, title: str) -> None:
        """Draw a meter bar with percentage"""
        meter_width = width - len(title) - 8
        filled = int(meter_width * percentage / 100)
        
        # Draw title
        self.screen.addstr(y, x, title, 
                          curses.color_pair(self.COLORS['meter_text'][2]))
        
        # Draw meter
        if percentage < 50:
            color = self.COLORS['cpu_low'][2]
        elif percentage < 80:
            color = self.COLORS['cpu_med'][2]
        else:
            color = self.COLORS['cpu_high'][2]
            
        self.screen.addstr(y, x + len(title), " [")
        self.screen.addstr(y, x + len(title) + 2, 
                          "|" * filled + " " * (meter_width - filled), 
                          curses.color_pair(color))
        self.screen.addstr(y, x + len(title) + 2 + meter_width, 
                          f"] {percentage:5.1f}%")

    def draw_header(self) -> None:
        """Draw the header bar with system info"""
        header = (f" System Monitor {self.update_interval}s | "
                 f"Sort[{self.sort_by}] | "
                 f"{'Tree' if self.tree_view else 'List'} | "
                 f"{'Threads' if self.show_threads else 'Processes'} | "
                 f"Press 'h' for help")
        self.screen.addstr(0, 0, header.ljust(curses.COLS), 
                          curses.color_pair(self.COLORS['header'][2]))

    def draw_system_info(self, y_pos: int) -> int:
        """Draw system information section"""
        if not self.current_metrics:
            return y_pos

        # CPU information
        cpus = self.current_metrics.get('cpu_usage', [])
        for i, usage in enumerate(cpus):
            self.draw_meter(y_pos + i, 1, curses.COLS - 2, 
                          usage, f"CPU{i:2d}")

        y_pos += len(cpus) + 1

        # Memory information
        mem = self.current_metrics.get('memory', {})
        if mem:
            total = mem.get('total', 0)
            used = mem.get('used', 0)
            if total > 0:
                mem_percent = (used / total) * 100
                self.draw_meter(y_pos, 1, curses.COLS - 2, 
                              mem_percent, "Mem ")
                
                details = (f"Total: {self.format_bytes(total)} | "
                          f"Used: {self.format_bytes(used)} | "
                          f"Free: {self.format_bytes(mem.get('free', 0))} | "
                          f"Buffers: {self.format_bytes(mem.get('buffers', 0))}")
                self.screen.addstr(y_pos + 1, 2, details)
                y_pos += 3

        return y_pos

    def draw_process_list(self, y_pos: int) -> None:
        """Draw the process list"""
        if 'processes' not in self.current_metrics:
            return

        # Header
        header = (" PID   USER     PR  NI    VIRT    RES    SHR S  %CPU  %MEM   TIME+   Command")
        self.screen.addstr(y_pos, 0, header, 
                          curses.color_pair(self.COLORS['header'][2]))
        y_pos += 1

        # Get and sort processes
        processes = self.current_metrics['processes']
        processes.sort(
            key=lambda x: x[self.sort_by],
            reverse=self.sort_reverse
        )

        # Calculate visible rows
        visible_rows = curses.LINES - y_pos - 1
        start_idx = self.scroll_offset
        end_idx = min(start_idx + visible_rows, len(processes))

        # Draw processes
        for i, proc in enumerate(processes[start_idx:end_idx], start=start_idx):
            color = (self.COLORS['highlight'][2] 
                    if i == self.selected_row 
                    else self.COLORS['normal'][2])
            
            # Format process information
            virt = self.format_bytes(proc.get('virt', 0))
            res = self.format_bytes(proc.get('mem_usage', 0))
            shr = self.format_bytes(proc.get('shared', 0))
            cpu = proc.get('cpu_usage', 0)
            mem = proc.get('mem_usage', 0) / self.current_metrics['memory']['total'] * 100

            line = (f" {proc['pid']:5d} {'root':8s} "
                   f"{proc.get('priority', 0):3d} {proc.get('nice', 0):3d} "
                   f"{virt:7s} {res:7s} {shr:7s} {proc['state']} "
                   f"{cpu:5.1f} {mem:5.1f} "
                   f"{'0:00.00':8s} {proc['name']}")

            try:
                self.screen.addstr(y_pos + i - start_idx, 0, 
                                 line.ljust(curses.COLS), 
                                 curses.color_pair(color))
            except curses.error:
                break  # Stop if we run out of screen space

    def draw_help(self) -> None:
        """Draw help overlay"""
        if not self.help_visible:
            return

        help_text = [
            "Help for System Monitor",
            "",
            "Keyboard commands:",
            "  h      - Show/hide this help",
            "  q      - Quit",
            "  Up/k   - Select previous process",
            "  Down/j - Select next process",
            "  Space  - Tag process",
            "  F5     - Tree view",
            "  F6     - Sort by",
            "  t      - Show threads",
            "  H      - Show thread",
            "",
            "Press any key to close help"
        ]

        # Calculate box dimensions
        height = len(help_text) + 2
        width = max(len(line) for line in help_text) + 4
        y = (curses.LINES - height) // 2
        x = (curses.COLS - width) // 2

        # Draw box
        self.screen.attron(curses.color_pair(self.COLORS['normal'][2]))
        for i in range(height):
            self.screen.addstr(y + i, x, " " * width)

        # Draw content
        for i, line in enumerate(help_text):
            self.screen.addstr(y + i + 1, x + 2, line)

        self.screen.attroff(curses.color_pair(self.COLORS['normal'][2]))

    async def handle_input(self) -> bool:
        """Handle user input"""
        try:
            self.screen.nodelay(1)
            key = self.screen.getch()
            
            if key == ord('q'):
                return False
            elif key == ord('h'):
                self.help_visible = not self.help_visible
            elif key == ord('t'):
                self.show_threads = not self.show_threads
            elif key == ord('F5'):
                self.tree_view = not self.tree_view
            elif key in (curses.KEY_UP, ord('k')):
                self.selected_row = max(0, self.selected_row - 1)
                if self.selected_row < self.scroll_offset:
                    self.scroll_offset = self.selected_row
            elif key in (curses.KEY_DOWN, ord('j')):
                max_row = len(self.current_metrics.get('processes', [])) - 1
                self.selected_row = min(max_row, self.selected_row + 1)
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
            y_pos = self.draw_system_info(y_pos)
            self.draw_process_list(y_pos)
            if self.help_visible:
                self.draw_help()
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
                        
                        await self.update_display()
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
    signal.signal(signal.SIGINT, lambda x, y: None)
    tui = MonitorTUI()
    asyncio.get_event_loop().run_until_complete(tui.run())

if __name__ == "__main__":
    main()