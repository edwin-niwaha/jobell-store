// =================================== Monthly sales for the current year ===================================
document.addEventListener("DOMContentLoaded", async function () {
  await fetchData();
});

async function fetchData() {
  try {
    const response = await fetch("/dashboard/monthly_earnings/");
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();

    renderLineChart(data.labels, data.data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderLineChart(labels, data) {
  var ctx = document.getElementById("myLineChart").getContext("2d");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Monthly Earnings",
          data: data,
          backgroundColor: "rgba(78, 115, 223, 0.2)",
          borderColor: "rgba(78, 115, 223, 1)",
          borderWidth: 2,
          pointRadius: 5,
          pointBackgroundColor: "rgba(78, 115, 223, 1)",
          pointBorderColor: "rgba(78, 115, 223, 1)",
          pointHoverRadius: 7,
          pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
          pointHoverBorderColor: "rgba(78, 115, 223, 1)",
          pointHitRadius: 10,
          pointBorderWidth: 2,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      layout: {
        padding: {
          left: 10,
          right: 25,
          top: 25,
          bottom: 0,
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            display: false,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            borderDash: [2],
            color: "rgb(234, 236, 244)",
            zeroLineColor: "rgb(234, 236, 244)",
          },
          ticks: {
            callback: function (value) {
              return numberFormat(value) + " $";
            },
          },
        },
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
        tooltip: {
          callbacks: {
            label: function (tooltipItem) {
              return `${tooltipItem.label}: ${numberFormat(tooltipItem.raw)} $`;
            },
          },
        },
      },
    },
  });
}

function numberFormat(
  number,
  decimals = 2,
  dec_point = ".",
  thousands_sep = ","
) {
  number = parseFloat(number).toFixed(decimals).toString();
  const [integer, decimal] = number.split(".");
  return (
    integer.replace(/\B(?=(?:\d{3})+(?!\d))/g, thousands_sep) +
    (decimal ? dec_point + decimal : "")
  );
}
