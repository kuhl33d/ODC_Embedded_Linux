// ui/web/static/js/monitor.js
class SystemMonitor {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.processTable = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.historyLength = 50;
        
        this.initializeWebSocket();
        this.initializeCharts();
        this.initializeProcessTable();
    }

    initializeWebSocket() {
        this.ws = new WebSocket('ws://localhost:8765');
        
        this.ws.onopen = () => {
            this.setConnectionStatus('connected');
            this.reconnectAttempts = 0;
            console.log('Connected to WebSocket server');
        };
        
        this.ws.onclose = () => {
            this.setConnectionStatus('disconnected');
            this.handleReconnect();
            console.log('WebSocket connection closed');
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.setConnectionStatus('disconnected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateMetrics(data);
            } catch (error) {
                console.error('Error processing message:', error);
            }
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
            const delay = this.reconnectDelay * this.reconnectAttempts;
            console.log(`Attempting to reconnect in ${delay}ms...`);
            setTimeout(() => this.initializeWebSocket(), delay);
        } else {
            console.log('Max reconnection attempts reached');
        }
    }

    initializeCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 500
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: value => value + '%'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        };

        // CPU Usage Chart
        this.charts.cpu = new Chart(document.getElementById('cpuChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage',
                    data: [],
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    title: {
                        display: true,
                        text: 'CPU Usage Over Time'
                    }
                }
            }
        });

        // Memory Usage Chart
        this.charts.memory = new Chart(document.getElementById('memoryChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    title: {
                        display: true,
                        text: 'Memory Usage Over Time'
                    }
                }
            }
        });

        // Memory Gauge
        this.charts.memoryGauge = new Chart(document.getElementById('memoryGauge'), {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Available'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [
                        '#4CAF50',
                        '#E0E0E0'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '85%',
                rotation: -90,
                circumference: 180,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    initializeProcessTable() {
        this.processTable = $('#processes-table').DataTable({
            columns: [
                { data: 'pid', title: 'PID' },
                { data: 'name', title: 'Name' },
                { 
                    data: 'cpu_usage',
                    title: 'CPU %',
                    render: (data) => `${parseFloat(data).toFixed(1)}%`
                },
                { 
                    data: 'mem_formatted',
                    title: 'Memory'
                },
                { data: 'state', title: 'State' },
                { 
                    data: 'priority',
                    title: 'Priority'
                }
            ],
            order: [[2, 'desc']],
            pageLength: 25,
            scrollY: '400px',
            scrollCollapse: true,
            dom: '<"top"f>rt<"bottom"lip>',
            language: {
                search: 'Filter processes:'
            },
            createdRow: function(row, data) {
                if (data.cpu_usage > 50) {
                    $(row).addClass('usage-high');
                } else if (data.cpu_usage > 20) {
                    $(row).addClass('usage-medium');
                }
            }
        });
    }

    updateMetrics(data) {
        if (!data) return;

        this.updateCPUMetrics(data.cpu_usage);
        this.updateMemoryMetrics(data.memory);
        this.updateProcesses(data.processes);
        this.updateCharts(data);
    }

    updateCPUMetrics(cpuData) {
        if (!cpuData) return;

        const container = document.getElementById('cpu-cores-container');
        container.innerHTML = '';

        cpuData.forEach((usage, index) => {
            if (usage > 0) {  // Only show active CPUs
                const coreElement = document.createElement('div');
                coreElement.className = 'cpu-core';
                
                let colorClass = 'usage-low';
                if (usage > 80) colorClass = 'usage-high';
                else if (usage > 50) colorClass = 'usage-medium';

                coreElement.innerHTML = `
                    <div class="cpu-core-label">Core ${index}</div>
                    <div class="cpu-core-bar">
                        <div class="cpu-core-bar-fill ${colorClass}" 
                             style="width: ${usage}%"></div>
                    </div>
                    <div class="cpu-core-value ${colorClass}">
                        ${usage.toFixed(1)}%
                    </div>
                `;
                container.appendChild(coreElement);
            }
        });
    }

    updateMemoryMetrics(memoryData) {
        if (!memoryData) return;

        document.getElementById('total-memory').textContent = 
            memoryData.total_formatted;
        document.getElementById('used-memory').textContent = 
            memoryData.used_formatted;
        document.getElementById('available-memory').textContent = 
            memoryData.free_formatted;

        const usagePercent = (memoryData.used / memoryData.total * 100);
        
        this.charts.memoryGauge.data.datasets[0].data = [
            usagePercent,
            100 - usagePercent
        ];
        this.charts.memoryGauge.update();

        // Update gauge color based on usage
        const color = usagePercent > 80 ? '#F44336' : 
                     usagePercent > 50 ? '#FFC107' : 
                     '#4CAF50';
        this.charts.memoryGauge.data.datasets[0].backgroundColor[0] = color;
        this.charts.memoryGauge.update();
    }

    updateProcesses(processes) {
        if (!processes) return;

        this.processTable.clear();
        this.processTable.rows.add(processes).draw();
    }

    updateCharts(data) {
        const timestamp = new Date().toLocaleTimeString();

        // Update CPU chart
        const cpuAverage = data.cpu_average || 
            (data.cpu_usage.reduce((a, b) => a + b, 0) / data.cpu_usage.length);

        if (this.charts.cpu.data.labels.length > this.historyLength) {
            this.charts.cpu.data.labels.shift();
            this.charts.cpu.data.datasets[0].data.shift();
        }
        this.charts.cpu.data.labels.push(timestamp);
        this.charts.cpu.data.datasets[0].data.push(cpuAverage.toFixed(1));
        this.charts.cpu.update();

        // Update Memory chart
        const memoryPercent = 
            (data.memory.used / data.memory.total * 100).toFixed(1);

        if (this.charts.memory.data.labels.length > this.historyLength) {
            this.charts.memory.data.labels.shift();
            this.charts.memory.data.datasets[0].data.shift();
        }
        this.charts.memory.data.labels.push(timestamp);
        this.charts.memory.data.datasets[0].data.push(memoryPercent);
        this.charts.memory.update();
    }
}

// Initialize the monitor when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SystemMonitor();
});