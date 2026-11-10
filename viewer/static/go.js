// Send the browser on to the results, replacing this page in its history so Back skips it.
(function () {
  var a = document.getElementById("go");
  if (a) location.replace(a.href);
})();
