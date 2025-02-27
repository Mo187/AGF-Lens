let chartInstance = null;
const UPDATE_INTERVAL = 30 * 60 * 1000; // 30 minutes in milliseconds
let updateTimer = null;
let isRequestInProgress = false; // Flag to prevent duplicate requests

function updateDOMEfficiently(data) {
    const impactScoreElement = document.getElementById('impactScore');
    const companyRiskScoreElement = document.getElementById('companyRiskScore');
    const totalEndpointsElement = document.getElementById('totalEndpoints');

    if (impactScoreElement) {
        const impactText = data.riskScore.impact;
        let impactColor;

        switch (impactText.toLowerCase()) {
            case 'low':
                impactColor = 'yellow';
                break;
            case 'medium':
                impactColor = 'orange';
                break;
            case 'high':
                impactColor = 'red';
                break;
            default:
                impactColor = 'grey';
        }

        impactScoreElement.innerText = impactText;
        impactScoreElement.style.color = impactColor;

        if (companyRiskScoreElement) {
            companyRiskScoreElement.innerText = data.riskScore.value;
            companyRiskScoreElement.style.color = impactColor;
        }
    }

    if (totalEndpointsElement) {
        totalEndpointsElement.innerText = data.totalEndpoints;
    }
}

function renderChart(data) {
    const chartElement = document.getElementById('riskScoreChart');
    if (!chartElement) return;
    
    const ctx = chartElement.getContext('2d');

    // Extract and clean data values
    const riskValues = [
        'appVulnerabilities', 'humanRisks', 'industryModifier', 
        'misconfigurations', 'value'
    ].map(key => {
        const rawValue = data.riskScore[key] || '0%';
        return Number(String(rawValue).replace('%', ''));
    });

    const riskScoreData = {
        labels: ['App Vulnerabilities', 'Human Risks', 'Industry Modifier', 'Misconfigurations', 'Risk Value'],
        datasets: [{
            label: 'Risk Score',
            data: riskValues,
            backgroundColor: ['#FF6384', '#36A2EB', '#4BC0C0', '#9966FF', '#FF9F40'],
            borderColor: ['#FF6384', '#36A2EB', '#4BC0C0', '#9966FF', '#FF9F40'],
            borderWidth: 1
        }]
    };

    if (chartInstance) {
        chartInstance.data = riskScoreData;
        chartInstance.update('none'); // Update without animation for better performance
    } else {
        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: riskScoreData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 300
                },
                transitions: {
                    active: {
                        animation: {
                            duration: 0  // No animation on updates
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { color: '#FFF' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#FFF' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        anchor: 'end',
                        align: 'top',
                        formatter: (value) => `${value}%`,
                        color: '#FFF',
                        font: { weight: 'bold' }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
    }
}

function fetchDashboardData() {
    // Prevent duplicate requests
    if (isRequestInProgress) {
        console.log("Request already in progress, skipping...");
        return;
    }
    
    console.log("Fetching dashboard data...");
    isRequestInProgress = true;
    
    fetch('/bitdefender_data', {
        method: 'GET',  // Explicitly set method to GET
        headers: {
            'Cache-Control': 'no-cache',  // Prevent browser caching
            'X-Requested-With': 'XMLHttpRequest'  // Indicate this is an AJAX request
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            isRequestInProgress = false;
            console.log("Data received:", data);

            if (!data || !data.riskScore) {
                throw new Error('Invalid data format');
            }

            // Update DOM and chart
            updateDOMEfficiently(data);
            renderChart(data);

            // Schedule next update
            scheduleNextUpdate();
        })
        .catch(error => {
            isRequestInProgress = false;
            console.error('Error fetching dashboard data:', error);
            // Retry after 1 minute on error
            scheduleNextUpdate(60000); // 1 minute retry
        });
}

function scheduleNextUpdate(interval = UPDATE_INTERVAL) {
    if (updateTimer) {
        clearTimeout(updateTimer);
    }
    updateTimer = setTimeout(fetchDashboardData, interval);
}

// Clear timer when page is hidden
function handleVisibilityChange() {
    if (document.hidden) {
        if (updateTimer) {
            clearTimeout(updateTimer);
            updateTimer = null;
        }
    } else {
        // Only fetch new data if we don't have an active timer and not already fetching
        if (!updateTimer && !isRequestInProgress) {
            fetchDashboardData();
        }
    }
}

// Initialize dashboard when DOM is loaded - use a self-executing function to ensure it only runs once
(function initDashboard() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard, { once: true });
        return;
    }
    
    // DOM is ready, initialize
    fetchDashboardData();
    document.addEventListener('visibilitychange', handleVisibilityChange);
})();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateTimer) {
        clearTimeout(updateTimer);
    }
});