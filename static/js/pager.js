/* Shows long lists a few items at a time, with Previous / Next.
 *
 *   <div data-pager="5"> ... <div data-pager-item>...</div> ... </div>
 *
 * Paging only hides items, so ticked checkboxes on other pages are still sent
 * with the form. Without JavaScript every item is simply shown.
 */
document.querySelectorAll("[data-pager]").forEach(function (list) {
  var size = parseInt(list.getAttribute("data-pager"), 10) || 5;
  var items = Array.prototype.slice.call(list.querySelectorAll("[data-pager-item]"));
  if (items.length <= size) return;
  var pages = Math.ceil(items.length / size), page = 0;

  var bar = document.createElement("div");
  bar.className = "pager";
  var prev = document.createElement("button"), next = document.createElement("button"), info = document.createElement("span");
  prev.type = next.type = "button";
  prev.className = next.className = "btn";
  prev.textContent = "Previous";
  next.textContent = "Next";
  info.className = "kpi";
  bar.appendChild(prev); bar.appendChild(info); bar.appendChild(next);
  list.parentNode.insertBefore(bar, list.nextSibling);  // after the list (it may be a table body)

  function show() {
    items.forEach(function (item, i) { item.style.display = Math.floor(i / size) === page ? "" : "none"; });
    info.textContent = "Page " + (page + 1) + " of " + pages + " · " + items.length + " items";
    prev.disabled = page === 0;
    next.disabled = page === pages - 1;
  }
  prev.addEventListener("click", function () { if (page > 0) { page--; show(); } });
  next.addEventListener("click", function () { if (page < pages - 1) { page++; show(); } });
  show();
});
