// The assistant bubble: a small chat on every page. It continues the user's latest chat, which is
// stored on the server, so the full chat page and the bubble always show the same conversation.
(function () {
  var root = document.querySelector(".ai-bubble");
  if (!root) { return; }
  var ball = root.querySelector(".ai-ball"), panel = root.querySelector(".ai-panel");
  var log = root.querySelector(".ai-log"), form = root.querySelector(".ai-form");
  var input = form.querySelector("input[name=question]"), chatField = form.querySelector("input[name=chat]");
  var file = form.querySelector("input[type=file]"), preview = form.querySelector(".ai-preview");
  var full = root.querySelector("[data-full]");
  var tokenField = form.querySelector("input[name=csrfmiddlewaretoken]");
  var token = tokenField ? tokenField.value : "";
  var loaded = false, busy = false;

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) { node.className = cls; }
    if (text) { node.textContent = text; }
    return node;
  }

  function render(m) {
    var box = el("div", "ai-msg " + m.role + (m.fallback ? " down-msg" : ""));
    if (m.photo) { var img = el("img"); img.src = m.photo; img.alt = "Photo you sent"; box.appendChild(img); }
    if (m.text) { box.appendChild(el("p", "", m.text)); }
    if (m.items && m.items.length) {
      var list = el("ul");
      m.items.forEach(function (item) {
        var li = el("li"), a = el("a", "", item.name); a.href = item.url; li.appendChild(a); list.appendChild(li);
      });
      box.appendChild(list);
    }
    if (m.page) { var go = el("a", "ai-go", m.page[0] + " →"); go.href = m.page[1]; box.appendChild(go); }
    if (m.role === "assistant" && !m.fallback) {
      var foot = el("div", "ai-foot");
      if (m.rating) { foot.textContent = m.rating; }
      else {
        foot.appendChild(el("span", "", "Helpful?"));
        [["yes", "Yes"], ["no", "No"]].forEach(function (pair) {
          var b = el("button", "", pair[1]); b.type = "button";
          b.addEventListener("click", function () { rateIt(m, pair[0], foot); });
          foot.appendChild(b);
        });
      }
      box.appendChild(foot);
    }
    log.appendChild(box);
    log.scrollTop = log.scrollHeight;
  }

  function post(url, data) {
    return fetch(url, { method: "POST", body: data, credentials: "same-origin",
                        headers: { "X-Requested-With": "fetch", "X-CSRFToken": token } })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); });
  }

  function rateIt(m, value, foot) {
    var data = new FormData(); data.append("helpful", value);
    post(m.rate, data).then(function (res) { foot.textContent = res.body.rating || "Thanks"; });
  }

  function load() {
    loaded = true;
    fetch(root.dataset.latestUrl, { credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.chat) { chatField.value = data.chat; full.href = data.chat_url; }
        if (!data.messages.length) {
          log.appendChild(el("p", "ai-hello", "Hi! Ask about items you can request, your requests, or how to do something. You can attach a photo too."));
        }
        data.messages.forEach(render);
      });
  }

  function setOpen(open) {
    panel.hidden = !open;
    ball.setAttribute("aria-expanded", open ? "true" : "false");
    root.classList.toggle("open", open);
    try { sessionStorage.setItem("aiBubbleOpen", open ? "1" : ""); } catch (e) { /* storage blocked */ }
    if (open) { if (!loaded) { load(); } input.focus(); }
  }

  ball.addEventListener("click", function () { setOpen(panel.hidden); });
  root.querySelector(".ai-close").addEventListener("click", function () { setOpen(false); });
  file.addEventListener("change", function () {
    if (!file.files[0]) { preview.hidden = true; return; }
    preview.querySelector("img").src = URL.createObjectURL(file.files[0]); preview.hidden = false;
  });
  preview.querySelector("[data-unattach]").addEventListener("click", function () { file.value = ""; preview.hidden = true; });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (busy || (!input.value.trim() && !file.files[0])) { return; }
    busy = true;
    var data = new FormData(form);
    var hello = log.querySelector(".ai-hello"); if (hello) { hello.remove(); }
    var typing = el("div", "ai-msg assistant typing", "Thinking…");
    log.appendChild(typing); log.scrollTop = log.scrollHeight;
    input.value = ""; file.value = ""; preview.hidden = true;
    post(root.dataset.sendUrl, data).then(function (res) {
      typing.remove();
      if (!res.ok) { log.appendChild(el("p", "ai-error", res.body.error || "Something went wrong.")); return; }
      chatField.value = res.body.chat; full.href = res.body.chat_url;
      res.body.messages.forEach(render);
    }).catch(function () {
      typing.remove(); log.appendChild(el("p", "ai-error", "The assistant could not be reached. Try again."));
    }).finally(function () { busy = false; input.focus(); });
  });

  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) { setOpen(false); } });
  try { if (sessionStorage.getItem("aiBubbleOpen")) { setOpen(true); } } catch (e) { /* storage blocked */ }
})();
