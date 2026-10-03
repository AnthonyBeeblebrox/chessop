// Counts one page view in the site's audience statistics, a self-hosted GoatCounter (public spec
// §12), whose count endpoint the script tag names in `data-goatcounter`. Served by the hosted
// site only, and only when that address is configured.
//
// Nothing is counted when the browser sends Do Not Track or Global Privacy Control, or when the
// privacy notice's toggle has set GoatCounter's `skipgc` flag. What is sent is the page's path
// without its query (so no UTM parameter or token), its title, and the referrer cut to its
// host: page views only, never the learner's cookie or account.
(function () {
  var endpoint = document.currentScript && document.currentScript.dataset.goatcounter;
  if (!endpoint) return;
  if (
    navigator.doNotTrack === "1" || window.doNotTrack === "1" ||
    navigator.globalPrivacyControl === true
  ) return;
  try {
    if (localStorage.getItem("skipgc") === "t") return;
  } catch (e) {
    // no local storage: no opt-out could have been kept
  }
  var referrer = "";
  try {
    if (document.referrer) referrer = new URL(document.referrer).host;
  } catch (e) {
    // not an address: left out
  }
  var view = {
    p: location.pathname,
    t: document.title,
    r: referrer,
    rnd: Math.random().toString(36).slice(2),
  };
  var url = endpoint + "?" + new URLSearchParams(view).toString();
  if (navigator.sendBeacon) navigator.sendBeacon(url);
  else new Image().src = url;
})();
