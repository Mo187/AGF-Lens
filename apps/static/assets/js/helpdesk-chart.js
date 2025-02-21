// Chart instances
let ticketVolumeChart = null;
let ticketStatusChart = null;

// Initialize ticket volume chart
function initTicketVolumeChart() {
    const ctx = document.getElementById('ticketVolumeChart').getContext('2d');
    ticketVolumeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Tickets Created',
                data: [],
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,  // Slightly thicker line
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 10,
                    right: 30,
                    top: 20,
                    bottom: 10
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        parser: 'YYYY-MM-DD',
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM D'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date',
                        color: '#ffffff'
                    },
                    ticks: {
                        color: '#ffffff',
                        maxRotation: 45,  // Adjust label rotation for better fit
                        minRotation: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Tickets',
                        color: '#ffffff'
                    },
                    ticks: {
                        color: '#ffffff',
                        padding: 10  // Add some padding to y-axis labels
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff',
                        font: {
                            size: 14
                        },
                        padding: 20
                    }
                },
                title: {
                    display: true,
                    text: 'Ticket Volume Over Time',
                    color: '#ffffff',
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 30
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    borderWidth: 1,
                    padding: 12
                }
            }
        }
    });
}

// Initialize ticket status chart
function initTicketStatusChart() {
    const ctx = document.getElementById('ticketStatusChart').getContext('2d');
    ticketStatusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#574b90',  // Open
                    '#1B9CFC',  // Pending
                    '#17a2b8',  // Resolved
                    '#2ed573',  // Closed
                    '#343a40'   // Unknown
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    bottom: 100  // Add padding for legend
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        // Force white color for legend text
                        color: '#ffffff !important',
                        font: {
                            size: 14,
                            weight: 'normal',
                            family: "'Helvetica', 'Arial', sans-serif"
                        },
                        padding: 20,
                        generateLabels: function(chart) {
                            var data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map(function(label, i) {
                                    var dataset = data.datasets[0];
                                    var value = dataset.data[i];
                                    var total = dataset.data.reduce((a, b) => a + b, 0);
                                    var percentage = ((value / total) * 100).toFixed(1);
                                    return {
                                        text: `${label} (${value} - ${percentage}%)`,
                                        fillStyle: dataset.backgroundColor[i],
                                        hidden: isNaN(dataset.data[i]) || chart.getDataVisibility(i),
                                        index: i,
                                        fontColor: '#ffffff'  // Additional attempt to force white text
                                    };
                                });
                            }
                            return [];
                        },
                        // Override the default label color
                        filter: function(legendItem, data) {
                            if (legendItem && legendItem.text) {
                                legendItem.fontColor = '#ffffff';  // Force white text
                            }
                            return true;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Ticket Status Distribution',
                    color: '#ffffff',
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: {
                        bottom: 30
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            var label = context.label || '';
                            var value = context.parsed || 0;
                            var total = context.dataset.data.reduce((a, b) => a + b, 0);
                            var percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // Additional attempt to force white text after chart creation
    if (ticketStatusChart.legend && ticketStatusChart.legend.options) {
        ticketStatusChart.legend.options.labels.color = '#ffffff';
    }
}
// Update function for the chart
function updateTicketStatusChart(statuses, counts, daysBack) {
    if (ticketStatusChart) {
        ticketStatusChart.data.labels = statuses;
        ticketStatusChart.data.datasets[0].data = counts;
        ticketStatusChart.options.plugins.title.text = 
            `Ticket Status Distribution (Last ${daysBack} Days)`;
        ticketStatusChart.update();
    }
}

// Update function remains the same but includes days_back in title
function updateTicketStatusChart(statuses, counts, daysBack) {
    if (ticketStatusChart) {
        ticketStatusChart.data.labels = statuses;
        ticketStatusChart.data.datasets[0].data = counts;
        ticketStatusChart.options.plugins.title.text = 
            `Ticket Status Distribution (Last ${daysBack} Days)`;
        ticketStatusChart.update();
    }
}
// Load basic stats
async function loadBasicStats() {
    try {
        console.log('Loading basic stats...');
        const response = await fetch('/api/helpdesk/basic-stats');
        const data = await response.json();
        console.log('Basic stats data:', data);

        if (data.error) {
            console.error('Error in basic stats:', data.error);
            return;
        }

        // Update the stats in the UI
        document.getElementById('total-unresolved').textContent = data.total_unresolved;
        document.getElementById('total-on-hold').textContent = data.total_on_hold;
        document.getElementById('total-open').textContent = data.total_open;
        document.getElementById('avg-resolution-time').textContent = 
            `${data.average_resolution_time.toFixed(2)} hours`;

        // Remove loading states
        document.querySelectorAll('.card-stats.loading').forEach(card => {
            card.classList.remove('loading');
        });
    } catch (error) {
        console.error('Error loading basic stats:', error);
    }
}

// Load and update charts
async function loadChartData() {
    try {
        console.log('Loading chart data...');
        const response = await fetch('/api/helpdesk/detailed-stats');
        const data = await response.json();
        console.log('Chart data:', data);

        if (data.error) {
            console.error('Error in chart data:', data.error);
            return;
        }

        // Update volume chart
        if (data.ticket_volume) {
            ticketVolumeChart.data.labels = data.ticket_volume.dates;
            ticketVolumeChart.data.datasets[0].data = data.ticket_volume.counts;
            ticketVolumeChart.update();
        }

        // Update status chart
        if (data.status_distribution) {
            ticketStatusChart.data.labels = data.status_distribution.statuses;
            ticketStatusChart.data.datasets[0].data = data.status_distribution.counts;
            ticketStatusChart.options.plugins.title.text = 
                `Ticket Status Distribution (Last ${data.status_distribution.days_back} Days)`;
            ticketStatusChart.update();
        }
    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Load recent activity
async function loadRecentActivity() {
    try {
        console.log('Loading recent activity...');
        const response = await fetch('/api/helpdesk/recent-activity');
        const data = await response.json();
        console.log('Recent activity data:', data);

        if (data.error) {
            console.error('Error in recent activity:', data.error);
            return;
        }

        // Update recent tickets
        const activityFeed = document.querySelector('.activity-feed');
        if (data.recent_tickets && activityFeed) {
            activityFeed.innerHTML = data.recent_tickets.map(ticket => `
                <li class="feed-item feed-item-secondary" style="color: rgb(212, 205, 206);">
                    <time class="date" datetime="${ticket.created_at}">${ticket.created_at}</time>
                    <div class="text" style="color: white;">
                        Ticket #${ticket.id} <a href="#">${ticket.subject}</a> is 
                        <span class="badge ${getStatusBadgeClass(ticket.status)}">${ticket.status}</span>
                    </div>
                    <div class="text">
                        <strong style="color:#9dbdf8;">Opened By: </strong> ${ticket.requester}
                    </div>
                    <div class="text">
                        <strong style="color: rgb(67, 160, 116);">Assigned To: </strong> ${ticket.agent}
                    </div>
                </li>
            `).join('');
        }

        // Update agent list
        const agentList = document.querySelector('.card-list');
        if (data.agent_names && agentList) {
            agentList.innerHTML = data.agent_names.map(name => `
                <div class="item-list">
                    <div class="avatar">
                        <img src="/static/assets/img/anya.png" alt="..." class="avatar-img rounded-circle">
                    </div>
                    <div class="info-user ml-3">
                        <div class="username">${name}</div>
                        <div class="status">IT Support Agent</div>
                    </div>
                    <button class="btn btn-icon btn-primary btn-round btn-xs">
                        <i class="fa fa-plus"></i>
                    </button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// Helper function for status badge classes
function getStatusBadgeClass(status) {
    const statusClasses = {
        'Open': 'badge-secondary',
        'Pending': 'badge-success',
        'Resolved': 'badge-info',
        'Closed': 'badge-success'
    };
    return statusClasses[status] || 'badge-dark';
}

// Initialize everything when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    
    // Initialize charts
    initTicketVolumeChart();
    initTicketStatusChart();
    
    // Load all data
    loadBasicStats();
    loadChartData();
    loadRecentActivity();
});

// Remove preloader when everything is loaded
window.addEventListener('load', function() {
    console.log('Window loaded, removing preloader...');
    const preloader = document.getElementById('preloader');
    if (preloader) {
        preloader.style.display = 'none';
    }
});