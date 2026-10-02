function showNoPermissionMessage(action) {
  let message =
    action === "edit"
      ? "Oops! You do not have permission to edit this record."
      : "Oops! You do not have permission to delete this record.";
  alert(message);
}

function showMessageDash(event) {
  event.preventDefault(); // Prevent the default link behavior
  // Open the contact page in a new tab and display a message
  if (
    confirm(
      'Oops! You do not have access rights to view this page. Please click "OK" to contact the administrator.'
    )
  ) {
    window.open("http://127.0.0.1:8000/contact-us/");
  }
}

function showMessageSettings(event) {
  // Prevent the default action of the event
  event.preventDefault();

  // Display an alert message
  alert("Oops! You do not have access rights.");
}
