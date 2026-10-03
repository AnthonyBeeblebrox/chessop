// The privacy notice's audience-statistics toggle (public spec §10, §12). Unticked, it sets
// GoatCounter's own opt-out flag, `skipgc`, in this browser's local storage, which the counting
// script (audience.js) reads; ticked again, it clears it. A browser sending Do Not Track or
// Global Privacy Control is never counted, and the box says so.
(function () {
  var box = document.getElementById("count-me");
  if (!box) return;
  var refused =
    navigator.doNotTrack === "1" || window.doNotTrack === "1" ||
    navigator.globalPrivacyControl === true;
  var skipped = false;
  try {
    skipped = localStorage.getItem("skipgc") === "t";
  } catch (e) {
    return; // no local storage: the flag cannot be kept, so the box stays as it is
  }
  box.checked = !refused && !skipped;
  box.disabled = refused;
  box.addEventListener("change", function () {
    try {
      if (box.checked) localStorage.removeItem("skipgc");
      else localStorage.setItem("skipgc", "t");
    } catch (e) {
      // nothing to keep it in
    }
  });
})();
