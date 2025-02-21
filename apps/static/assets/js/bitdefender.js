let chartInstance = null;
const UPDATE_INTERVAL = 30 * 60 * 1000; // 30 minutes in milliseconds
let updateTimer = null;

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
    const ctx = document.getElementById('riskScoreChart').getContext('2d');

    const riskScoreData = {
        labels: ['App Vulnerabilities', 'Human Risks', 'Industry Modifier', 'Misconfigurations', 'Risk Value'],
        datasets: [{
            label: 'Risk Score',
            data: [
                parseFloat(data.riskScore.appVulnerabilities),
                parseFloat(data.riskScore.humanRisks),
                parseFloat(data.riskScore.industryModifier),
                parseFloat(data.riskScore.misconfigurations),
                parseFloat(data.riskScore.value)
            ].map(value => Number(String(value).replace('%', ''))),
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
                    duration: 1000
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
    console.log("Fetching dashboard data...");
    fetch('/bitdefender_data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Data received:", data);

            if (!data || !data.riskScore) {
                throw new Error('Invalid data format');
            }

            // Update DOM and chart
            updateDOMEfficiently(data);
            renderChart(data);

            // Schedule next update
            if (updateTimer) {
                clearTimeout(updateTimer);
            }
            updateTimer = setTimeout(fetchDashboardData, UPDATE_INTERVAL);
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            // Retry after 1 minute on error
            if (updateTimer) {
                clearTimeout(updateTimer);
            }
            updateTimer = setTimeout(fetchDashboardData, 60000);
        });
}

// Clear timer when page is hidden
function handleVisibilityChange() {
    if (document.hidden) {
        if (updateTimer) {
            clearTimeout(updateTimer);
            updateTimer = null;
        }
    } else {
        // Only fetch new data if we don't have an active timer
        if (!updateTimer) {
            fetchDashboardData();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardData();
    document.addEventListener('visibilitychange', handleVisibilityChange);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateTimer) {
        clearTimeout(updateTimer);
    }
});