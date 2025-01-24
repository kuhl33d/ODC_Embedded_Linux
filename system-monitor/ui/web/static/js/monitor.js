// ui/web/static/js/monitor.js
class SystemMonitor {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.processTable = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.initializeWebSocket();
        this.initializeCharts();
        this.initializeProcessTable();
    }

    initializeWebSocket() {
        this.ws = new WebSocket('ws://localhost:8765');
        
        this.ws.onopen = () => {
            this.setConnectionStatus('connected');
            this.reconnectAttempts = 0;
        };
        
        this.ws.onclose = () => {
            this.setConnectionStatus('disconnected');
            this.handleReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.setConnectionStatus('disconnected');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateMetrics(data);
        };
    }

    setConnectionStatus(status) {
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        
        indicator.className = status;
        statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                this.initializeWebSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    initializeCharts() {
        // CPU Usage Chart
        this.charts.cpu = new Chart(document.getElementById('cpuChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage %',
                    data: [],
                    borderColor: '#2196F3',
                    tension: 0.4,
                    fill: false
                }]
            },
            options: this.getChartOptions('CPU Usage Over Time')
        });

        // Memory Usage Chart
        this.charts.memory = new Chart(document.getElementById('memoryChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage %',
                    data: [],
                    borderColor: '#4CAF50',
                    tension: 0.4,
                    fill: false
                }]
            },
            options: this.getChartOptions('Memory Usage Over Time')
        });

        // Memory Gauge
        this.charts.memoryGauge = new Chart(document.getElementById('memoryGauge'), {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Free'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#4CAF50', '#e0e0e0']
                }]
            },
            options: {
                cutout: '80%',
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    getChartOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        };
    }

    initializeProcessTable() {
        this.processTable = $('#processes-table').DataTable({
            columns: [
                { data: 'pid' },
                { data: 'name' },
                { data: 'cpu_usage' },
                { data: 'memory_usage' },
                { data: 'state' }
            ],
            order: [[2, 'desc']],
            pageLength: 25,
            scrollY: '400px',
            scrollCollapse: true
        });
    }

    updateMetrics(data) {
        this.updateCPUMetrics(data.cpu_usage);
        this.updateMemoryMetrics(data.memory);
        this.updateProcesses(data.processes);
        this.updateCharts(data);
    }

    updateCPUMetrics(cpuData) {
        const container = document.getElementById('cpu-cores-container');
        container.innerHTML = '';

        cpuData.forEach((usage, index) => {
            const coreElement = document.createElement('div');
            coreElement.className = 'cpu-core';
            coreElement.innerHTML = `
                <div class="cpu-core-label">Core ${index}</div>
                <div class="cpu-core-bar">
                    <div class="cpu-core-bar-fill" style="width: ${usage}%"></div>
                </div>
                <div class="cpu-core-value">${usage.toFixed(1)}%</div>
            `;
            container.appendChild(coreElement);
        });
    }

    updateMemoryMetrics(memoryData) {
        const totalGB = this.formatBytes(memoryData.total);
        const usedGB = this.formatBytes(memoryData.used);
        const availableGB = this.formatBytes(memoryData.available);
        const usagePercent = (memoryData.used / memoryData.total * 100).toFixed(1);

        document.getElementById('total-memory').textContent = totalGB;
        document.getElementById('used-memory').textContent = usedGB;
        document.getElementById('available-memory').textContent = availableGB;

        this.charts.memoryGauge.data.datasets[0].data = [
            parseFloat(usagePercent),
            100 - parseFloat(usagePercent)
        ];
        this.charts.memoryGauge.update();
    }

    updateProcesses(processes) {
        this.processTable.clear();
        this.processTable.rows.add(processes.map(process => ({
            pid: process.pid,
            name: process.name,
            cpu_usage: process.cpu_usage.toFixed(1) + '%',
            memory_usage: process.memory_usage.toFixed(1) + '%',
            state: process.state
        })));
        this.processTable.draw();
    }

    updateCharts(data) {
        const timestamp = new Date().toLocaleTimeString();

        // Update CPU chart
        if (this.charts.cpu.data.labels.length > 50) {
            this.charts.cpu.data.labels.shift();
            this.charts.cpu.data.datasets[0].data.shift();
        }
        this.charts.cpu.data.labels.push(timestamp);
        this.charts.cpu.data.datasets[0].data.push(
            (data.cpu_usage.reduce((a, b) => a + b, 0) / data.cpu_usage.length).toFixed(1)
        );
        this.charts.cpu.update();

        // Update Memory chart
        if (this.charts.memory.data.labels.length > 50) {
            this.charts.memory.data.labels.shift();
            this.charts.memory.data.datasets[0].data.shift();
        }
        this.charts.memory.data.labels.push(timestamp);
        this.charts.memory.data.datasets[0].data.push(
            (data.memory.used / data.memory.total * 100).toFixed(1)
        );
        this.charts.memory.update();
    }

    formatBytes(bytes) {
        const gb = bytes / (1024 * 1024 * 1024);
        return gb.toFixed(2) + ' GB';
    }
}

// Initialize the monitor when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SystemMonitor();
});