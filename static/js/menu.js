// Profile menu: close it when the user clicks anywhere else or presses Escape.
document.addEventListener("click", function (event) {
  document.querySelectorAll("details.usermenu[open]").forEach(function (menu) {
    if (!menu.contains(event.target)) { menu.removeAttribute("open"); }
  });
});
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    document.querySelectorAll("details.usermenu[open]").forEach(function (menu) { menu.removeAttribute("open"); });
  }
});
