function validateForm() {
  var selectedProduct = document.getElementById("dropdown").value;

  if (selectedProduct === "") {
    alert("Please select a product!");
    return false;
  }

  return true;
}
