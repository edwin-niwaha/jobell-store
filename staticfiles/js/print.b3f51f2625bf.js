// print div
function printDiv(divName) {
  var printContents = document.getElementById(divName).innerHTML;
  var originalContents = document.body.innerHTML;

  document.body.innerHTML = printContents;

  window.print();

  document.body.innerHTML = originalContents;
}

// convert to excel format
function ExportToExcel(type, fn, dl) {
  var elt = document.getElementById("printMe");
  var wb = XLSX.utils.table_to_book(elt, { sheet: "sheet1" });
  return dl
    ? XLSX.write(wb, { bookType: type, bookSST: true, type: "base64" })
    : XLSX.writeFile(wb, fn || "jobell_rpt." + (type || "xlsx"));
}

// Convert to word document
function Export2Doc(element, filename = "") {
  var html =
    "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta><title>Export HTML To Doc</title></head><body>";
  var footer = "</body></html>";
  var html = html + document.getElementById(element).innerHTML + footer;

  //link url
  var url =
    "data:application/vnd.ms-word;charset=utf-8," + encodeURIComponent(html);

  //file name
  filename = filename ? filename + ".doc" : "jobell_rpt.doc";

  // Creates the  download link element dynamically
  var downloadLink = document.createElement("a");

  document.body.appendChild(downloadLink);

  //Link to the file
  downloadLink.href = url;

  //Setting up file name
  downloadLink.download = filename;

  //triggering the function
  downloadLink.click();
  //Remove the a tag after donwload starts.
  document.body.removeChild(downloadLink);
}
