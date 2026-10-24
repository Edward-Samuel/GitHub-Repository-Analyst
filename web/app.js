const repository = document.querySelector("#repository");
const loadButton = document.querySelector("#load-button");
const question = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const form = document.querySelector("#chat-form");
const messages = document.querySelector("#messages");
const status = document.querySelector("#status");
const repoCard = document.querySelector("#repo-card");
const repoLoading = document.querySelector("#repo-loading");
const repoLoadingLabel = document.querySelector("#repo-loading-label");
const chatLoading = document.querySelector("#chat-loading");
const chatLoadingLabel = document.querySelector("#chat-loading-label");
let loadedRepository = "";

function renderMarkdown(text) {
  if (window.marked && window.DOMPurify) {
    return DOMPurify.sanitize(marked.parse(text));
  }

  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const lines = escaped.split(/\r?\n/);
  const output = [];
  let paragraph = [];
  let listType = null;
  let listItems = [];
  let inCode = false;
  let codeLanguage = "text";
  let codeLines = [];

  const inline = value => value
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");

  const flushParagraph = () => {
    if (paragraph.length) {
      output.push(`<p>${inline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  };

  const flushList = () => {
    if (listItems.length) {
      output.push(`<${listType}>${listItems.join("")}</${listType}>`);
      listItems = [];
      listType = null;
    }
  };

  const flushCode = () => {
    output.push(
      `<pre><code class="language-${codeLanguage}">${codeLines.join("\n")}</code></pre>`
    );
    codeLines = [];
    codeLanguage = "text";
  };

  for (const line of lines) {
    const fence = line.match(/^```([\w+-]*)\s*$/);
    if (fence) {
      flushParagraph();
      flushList();
      if (inCode) {
        flushCode();
      } else {
        inCode = true;
        codeLanguage = fence[1] || "text";
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);

    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      output.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    } else if (unordered || ordered) {
      flushParagraph();
      const nextType = unordered ? "ul" : "ol";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      listItems.push(`<li>${inline((unordered || ordered)[1])}</li>`);
    } else if (!line.trim()) {
      flushParagraph();
      flushList();
    } else {
      flushList();
      paragraph.push(line.trim());
    }
  }

  if (inCode) flushCode();
  flushParagraph();
  flushList();
  return output.join("");
}

function addMessage(role, text, markdown = false) {
  const empty = messages.querySelector(".welcome");
  if (empty) empty.remove();
  const row = document.createElement("div");
  row.className = `message ${role}`;
  row.innerHTML = role === "assistant"
    ? `<div class="avatar">✦</div><div class="bubble"></div>`
    : `<div class="bubble"></div>`;
  const bubble = row.querySelector(".bubble");
  if (markdown) {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

async function loadRepo() {
  const value = repository.value.trim();
  if (!value || loadButton.disabled) return;

  loadButton.disabled = true;
  loadButton.textContent = "Loading…";
  repository.disabled = true;
  repoLoading.classList.remove("hidden");
  repoLoading.setAttribute("aria-busy", "true");
  repoLoadingLabel.textContent = "Fetching repository details, files, and README…";
  status.textContent = "Loading repository…";

  try {
    const response = await fetch("/api/repository", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repository: value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load repository");

    loadedRepository = data.repository.full_name || value;
    repoCard.classList.remove("hidden");
    repoCard.innerHTML = `<strong>${data.repository.full_name}</strong><span>${data.repository.description || "No description"}<br>${data.file_count.toLocaleString()} files · ${data.loaded_files.length} files loaded for chat</span>`;
    status.textContent = "Repository loaded. Ask a question.";
    question.disabled = false;
    sendButton.disabled = false;
    question.focus();
  } catch (error) {
    status.textContent = error.message || "Unable to load repository. Please try again.";
  } finally {
    repoLoading.classList.add("hidden");
    repoLoading.setAttribute("aria-busy", "false");
    loadButton.disabled = false;
    loadButton.textContent = "Load";
    repository.disabled = false;
  }
}

loadButton.addEventListener("click", loadRepo);
repository.addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadRepo();
  }
});
document.querySelectorAll(".suggestions button").forEach(button => button.addEventListener("click", () => {
  question.value = button.textContent; question.focus();
}));
question.addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.isComposing) {
    event.preventDefault();
    if (!sendButton.disabled) form.requestSubmit(sendButton);
  }
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text || !loadedRepository || sendButton.disabled) return;
  addMessage("user", text);
  question.value = "";
  question.disabled = true;
  sendButton.disabled = true;
  status.textContent = "Preparing your answer…";
  chatLoadingLabel.textContent = "Contacting the AI service…";
  chatLoading.classList.remove("hidden");
  let assistantBubble = null;
  let answer = "";
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repository: loadedRepository, question: text})
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Unable to answer");
    }
    chatLoadingLabel.textContent = "Generating your answer…";
    assistantBubble = addMessage("assistant", "", true);
    if (!response.body) {
      throw new Error("Streaming is not supported by this browser.");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let done = false;
    while (!done) {
      const result = await reader.read();
      done = result.done;
      buffer += decoder.decode(result.value || new Uint8Array(), {stream: !done});
      // SSE events may use LF or CRLF line endings.
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() || "";
      // Process an unterminated final event when the connection closes.
      if (done && buffer.trim()) {
        events.push(buffer);
        buffer = "";
      }
      for (const event of events) {
        const dataLines = event.split(/\r?\n/).filter(item => item.startsWith("data:"));
        if (!dataLines.length) continue;
        const rawPayload = dataLines.map(item => item.slice(5).trim()).join("\n").trim();
        if (!rawPayload || rawPayload === "[DONE]" || rawPayload === '"[DONE]"') {
          done = rawPayload.includes("[DONE]") || done;
          if (done) break;
          continue;
        }
        let payload;
        try {
          payload = JSON.parse(rawPayload);
        } catch {
          throw new Error("Received an invalid streaming response from the server.");
        }
        // Handle a JSON-quoted completion marker from proxies or compatible servers.
        if (payload === "[DONE]") {
          done = true;
          break;
        }
        if (payload && typeof payload === "object" && payload.error) {
          throw new Error(payload.error);
        }
        if (payload && typeof payload === "object" && typeof payload.text === "string") {
          if (payload.text) {
            answer += payload.text;
            chatLoading.classList.add("hidden");
            assistantBubble.innerHTML = renderMarkdown(answer);
            messages.scrollTop = messages.scrollHeight;
          }
        }
      }
    }
    chatLoading.classList.add("hidden");
    status.textContent = "Ready for another question.";
  } catch (error) {
    chatLoading.classList.add("hidden");
    const rawMessage = error && error.message ? error.message : "An unexpected error occurred.";
    const temporaryFailure = /Gemini API error (500|502|503|504)|temporarily unavailable|\[DONE\].*not valid JSON/i.test(rawMessage);
    const friendlyMessage = temporaryFailure
      ? "The AI service ran into a temporary problem. Please try again in a moment."
      : `I couldn't complete the answer: ${rawMessage}`;
    const finalMessage = answer
      ? `${answer}\n\n---\n\n**Response interrupted:** ${friendlyMessage}`
      : friendlyMessage;
    if (assistantBubble) {
      assistantBubble.innerHTML = renderMarkdown(finalMessage);
    } else {
      addMessage("assistant", finalMessage, true);
    }
    status.textContent = "Couldn't complete the answer. You can try again.";
  }
  finally { question.disabled = false; sendButton.disabled = false; question.focus(); }
});
