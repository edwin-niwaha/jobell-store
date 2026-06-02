// Function to fetch the sales data asynchronously
async function fetchSalesData() {
  try {
    const response = await fetch("/dashboard/sales-data/"); // Make sure this matches your API endpoint
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json(); // Parse the JSON response
    return data;
  } catch (error) {
    console.error("Error fetching sales data:", error);
    return null; // Return null if there was an error
  }
}

// Function to render the chart using Chart.js
async function renderChart() {
  const salesData = await fetchSalesData();

  // if (!salesData) {
  //   alert("Failed to load sales data.");
  //   return;
  // }

  const ctx = document.getElementById("salesChart").getContext("2d");
  const salesChart = new Chart(ctx, {
    type: "line", // Use a line chart
    data: {
      labels: salesData.years, // X-axis labels (years)
      datasets: [
        {
          label: "Total Sales",
          data: salesData.total_sales, // Y-axis data (total sales)
          borderColor: "rgba(75, 192, 192, 1)",
          backgroundColor: "rgba(75, 192, 192, 0.2)",
          borderWidth: 2,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}

// Call the function to render the chart when the page loads
renderChart();
