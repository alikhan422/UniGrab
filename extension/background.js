chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "unigrab_download_link",
    title: "Download with UniGrab",
    contexts: ["link", "video", "audio", "page"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const targetUrl = info.linkUrl || info.srcUrl || info.pageUrl || "";
  if (!targetUrl) return;

  fetch("http://127.0.0.1:49814/download", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ url: targetUrl })
  }).catch((err) => {
    console.log("UniGrab desktop client not running or unreachable:", err);
  });
});

chrome.action.onClicked.addListener((tab) => {
  if (tab && tab.url) {
    fetch("http://127.0.0.1:49814/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: tab.url })
    }).catch((err) => {
      console.log("UniGrab desktop client unreachable:", err);
    });
  }
});
