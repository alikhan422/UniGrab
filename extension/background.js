const UNIGRAB_ENDPOINT = "http://127.0.0.1:49814/";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "unigrab_download_link",
      title: "Download with UniGrab",
      contexts: ["link", "video", "audio"]
    });
    chrome.contextMenus.create({
      id: "unigrab_download_page",
      title: "Download Page Media with UniGrab",
      contexts: ["page"]
    });
  });
});

if (chrome.contextMenus && chrome.contextMenus.onClicked) {
  chrome.contextMenus.onClicked.addListener((info, tab) => {
    let targetUrl = info.linkUrl || info.srcUrl || info.pageUrl;
    if (targetUrl) {
      sendToUniGrab(targetUrl);
    }
  });
}

if (chrome.action && chrome.action.onClicked) {
  chrome.action.onClicked.addListener((tab) => {
    if (tab && tab.url) {
      sendToUniGrab(tab.url);
    }
  });
}

function sendToUniGrab(url) {
  fetch(UNIGRAB_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: url })
  }).catch((err) => {
    console.log("UniGrab not reachable or running in background:", err);
  });
}
