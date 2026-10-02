// serch table
$(document).ready(function () {
  $("#searchInput").on("keyup", function () {
    var value = $(this).val().toLowerCase();
    $("#dataTable tr").filter(function () {
      $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
    });
  });
});

// search form
// JavaScript for Real-time Search
document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("searchInput");
  const productList = document.getElementById("search_list");
  if (!searchInput || !productList) return;

  searchInput.addEventListener("keyup", function () {
    const filter = searchInput.value.toLowerCase();
    const items = productList.getElementsByClassName("product-item");

    Array.from(items).forEach(function (item) {
      const title = item.querySelector(".card-title").textContent.toLowerCase();
      const category = item
        .querySelector(".card-text")
        .textContent.toLowerCase();

      if (title.includes(filter) || category.includes(filter)) {
        item.style.display = "";
      } else {
        item.style.display = "none";
      }
    });
  });
});
