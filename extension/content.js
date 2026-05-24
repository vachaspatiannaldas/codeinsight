function extractPRDiff() {
  const diffElements = document.querySelectorAll(
    ".blob-code-addition .blob-code-inner, .blob-code-deletion .blob-code-inner, .js-file-line"
  );

  let diffText = "";

  diffElements.forEach((el) => {
    const line = el.innerText.trimEnd();

    if (line) {
      diffText += line + "\n";
    }
  });

  console.log("Extracted Diff:", diffText);

  return diffText;
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "GET_PR_DIFF") {
    const diff = extractPRDiff();

    sendResponse({
      diff,
    });
  }
});