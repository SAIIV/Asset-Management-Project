// Profile menu: close it when the user clicks anywhere else or presses Escape.
document.addEventListener("click", function (event) {
  document.querySelectorAll("details.usermenu[open]").forEach(function (menu) {
    if (!menu.contains(event.target)) { menu.removeAttribute("open"); }
  });
});

// Main menu behind the ☰ button: open and close, close on Escape or a click on the dimmed page.
(function () {
  var button = document.querySelector(".menu-btn");
  if (!button) { return; }
  var bar = document.querySelector(".topbar");
  function setOpen(open) {
    document.body.classList.toggle("menu-open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      document.body.style.setProperty("--top", bar.getBoundingClientRect().bottom + "px");
      var search = document.querySelector(".launcher-search input");
      if (search) { search.focus(); }
    }
  }
  button.addEventListener("click", function () { setOpen(!document.body.classList.contains("menu-open")); });
  document.querySelector(".scrim").addEventListener("click", function () { setOpen(false); });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setOpen(false);
      document.querySelectorAll("details.usermenu[open]").forEach(function (menu) { menu.removeAttribute("open"); });
    }
  });
})();
