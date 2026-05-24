const analyzeBtn = document.getElementById("analyzeBtn");
const statusDiv = document.getElementById("status");
const resultsDiv = document.getElementById("results");

analyzeBtn.addEventListener("click", async () => {
  resultsDiv.innerHTML = "";
  statusDiv.innerText = "Extracting PR diff...";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab?.url) {
    statusDiv.innerText = "Could not read the current tab URL.";
    return;
  }

  let diff = "";

  try {
    diff = await fetchPullRequestDiff(tab.url);
  } catch (err) {
    console.warn("Could not fetch .diff URL, falling back to page extraction", err);
    diff = await extractDiffFromPage(tab.id);
  }

  diff = diff.trim();

  if (!diff) {
    statusDiv.innerText =
      "No PR diff found. Make sure this is a GitHub pull request page and reload the extension.";
    return;
  }

  statusDiv.innerText = "Sending to AI backend...";

  let reviewData;

  try {
    reviewData = await requestJson("http://127.0.0.1:8000/api/review/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_name: getRepositoryName(tab.url),
        pr_number: getPullRequestNumber(tab.url),
        diff,
      }),
    });
  } catch (err) {
    statusDiv.innerText = err.message;
    console.error(err);
    return;
  }

  const reviewId = reviewData.review_id;

  if (!reviewId) {
    statusDiv.innerText = "Backend did not return a review id.";
    console.error("Unexpected backend response:", reviewData);
    return;
  }

  statusDiv.innerText = "Analyzing PR...";
  pollReview(reviewId);
});

async function fetchPullRequestDiff(tabUrl) {
  const diffUrl = getPullRequestDiffUrl(tabUrl);

  if (!diffUrl) {
    throw new Error("Current page is not a GitHub pull request URL.");
  }

  const res = await fetch(diffUrl, {
    credentials: "include",
    headers: { Accept: "text/plain" },
  });

  const text = await res.text();

  if (!res.ok) {
    throw new Error(`GitHub diff request failed (${res.status}).`);
  }

  if (text.trim().startsWith("<!DOCTYPE")) {
    throw new Error("GitHub returned HTML instead of diff text.");
  }

  return text;
}

function extractDiffFromPage(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "GET_PR_DIFF" }, (response) => {
      if (chrome.runtime.lastError) {
        console.error(chrome.runtime.lastError.message);
        resolve("");
        return;
      }

      resolve(response?.diff || "");
    });
  });
}

async function pollReview(reviewId) {
  const interval = setInterval(async () => {
    try {
      const data = await requestJson(
        `http://127.0.0.1:8000/api/review/${reviewId}/`
      );

      if (data.status === "completed") {
        clearInterval(interval);
        renderResults(data);
      }

      if (data.status === "failed") {
        clearInterval(interval);
        statusDiv.innerText = data.ai_response?.error || "Review failed in backend.";
      }
    } catch (err) {
      clearInterval(interval);
      statusDiv.innerText = err.message;
      console.error(err);
    }
  }, 3000);
}

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();

  let data;

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(
      `Backend returned non-JSON response (${res.status}). Check that ${url} is hitting the Django API.`
    );
  }

  if (!res.ok) {
    throw new Error(
      data.error || data.detail || `Backend request failed (${res.status}).`
    );
  }

  return data;
}

function getPullRequestParts(url) {
  try {
    const parsedUrl = new URL(url);
    const parts = parsedUrl.pathname.split("/").filter(Boolean);
    const pullIndex = parts.indexOf("pull");

    if (parsedUrl.hostname !== "github.com" || pullIndex !== 2) {
      return null;
    }

    const owner = parts[0];
    const repo = parts[1];
    const prNumber = Number(parts[3]);

    if (!owner || !repo || !prNumber) {
      return null;
    }

    return { owner, repo, prNumber };
  } catch {
    return null;
  }
}

function getPullRequestDiffUrl(url) {
  const parts = getPullRequestParts(url);
  return parts
    ? `https://github.com/${parts.owner}/${parts.repo}/pull/${parts.prNumber}.diff`
    : "";
}

function getRepositoryName(url) {
  const parts = getPullRequestParts(url);
  return parts ? `${parts.owner}/${parts.repo}` : "github-pr";
}

function getPullRequestNumber(url) {
  const parts = getPullRequestParts(url);
  return parts ? parts.prNumber : 1;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderResults(data) {
  statusDiv.innerText = "Review Completed";
  resultsDiv.innerHTML = "";

  const issues = data.ai_response?.issues || [];

  if (!issues.length) {
    resultsDiv.innerText = "No valid issues returned by AI.";
    return;
  }

  issues.forEach((issue) => {
    const div = document.createElement("div");
    div.className = "issue";

    div.innerHTML = `
      <div class="file-name">${escapeHtml(issue.file || "unknown file")}</div>
      <div class="issue-header">
        <div class="category">${escapeHtml(issue.category || "quality")}</div>
        <div class="severity ${escapeHtml(issue.severity || "medium")}">${escapeHtml(issue.severity || "medium")}</div>
      </div>

      <p class="message">${escapeHtml(issue.message || "No message provided.")}</p>

      <div class="suggestion-box">
        <p class="section-label">Suggestion</p>
        <p>${escapeHtml(issue.suggestion || "No suggestion provided.")}</p>
      </div>

      <p class="section-title">Vulnerable Code</p>
      <pre class="vulnerable-code"><code>${escapeHtml(issue.vulnerable_code || "No vulnerable code returned.")}</code></pre>

      <p class="section-title">Recommended Fix</p>
      <pre class="fixed-code"><code>${escapeHtml(issue.fixed_code || "No fix provided.")}</code></pre>
    `;

    resultsDiv.appendChild(div);
  });
}


