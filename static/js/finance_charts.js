// Function to initialize all charts
function initializeCharts() {
    // Helper function to create a chart
    function createChart(canvasId, type, data, options) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, { type, data, options });
    }

    // 1. Bar Chart: Transaction Totals by Account Type
    fetch('/dashboard/transactions_by_account_type/')
        .then(response => response.json())
        .then(data => {
            createChart('accountTypeChart', 'bar', {
                labels: data.labels,
                datasets: [{
                    label: 'Total Transaction Amount',
                    data: data.amounts,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            }, {
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Amount ($)' } },
                    x: { title: { display: true, text: 'Account Type' } }
                },
                plugins: {
                    title: { display: true, text: 'Transaction Totals by Account Type' }
                }
            });
        })
        .catch(error => console.error('Error loading account type chart:', error));

    // 2. Pie Chart: Financial Period Status Distribution
    fetch('/dashboard/financial_period_status/')
        .then(response => response.json())
        .then(data => {
            createChart('periodStatusChart', 'pie', {
                labels: data.labels,
                datasets: [{
                    label: 'Financial Period Status',
                    data: data.counts,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.2)',
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 206, 86, 0.2)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            }, {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'Financial Period Status Distribution' }
                }
            });
        })
        .catch(error => console.error('Error loading period status chart:', error));

    // 3. Line Chart: Transaction Trends Over Time
    fetch('/dashboard/transaction_trends/')
        .then(response => response.json())
        .then(data => {
            createChart('transactionTrendsChart', 'line', {
                labels: data.labels,
                datasets: [{
                    label: 'Transaction Amount',
                    data: data.amounts,
                    fill: false,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.1
                }]
            }, {
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Amount ($)' } },
                    x: { title: { display: true, text: 'Date' } }
                },
                plugins: {
                    title: { display: true, text: 'Transaction Trends Over Time' }
                }
            });
        })
        .catch(error => console.error('Error loading transaction trends chart:', error));


    // 4. Donut Chart: Top Accounts by Transaction Volume
    fetch('/dashboard/top_accounts/')
        .then(response => response.json())
        .then(data => {
            createChart('topAccountsChart', 'doughnut', {
                labels: data.labels,
                datasets: [{
                    label: 'Transaction Volume',
                    data: data.amounts,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.2)',
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 206, 86, 0.2)',
                        'rgba(75, 192, 192, 0.2)',
                        'rgba(153, 102, 255, 0.2)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            }, {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'Top 5 Accounts by Transaction Volume' }
                }
            });
        })
        .catch(error => console.error('Error loading top accounts chart:', error));

    fetch('/dashboard/income_vs_expenses/')
        .then(response => response.json())
        .then(data => {
            createChart('incomeVsExpensesChart', 'line', {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Income',
                        data: data.income,
                        fill: false,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Expenses',
                        data: data.expenses,
                        fill: false,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    }
                ]
            }, {
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Amount ($)' } },
                    x: { title: { display: true, text: 'Date' } }
                },
                plugins: {
                    title: { display: true, text: 'Income vs Expenses' }
                }
            });
        })
        .catch(error => console.error('Error loading income vs expenses chart:', error));

}

// Initialize charts when the DOM is loaded
document.addEventListener('DOMContentLoaded', initializeCharts);