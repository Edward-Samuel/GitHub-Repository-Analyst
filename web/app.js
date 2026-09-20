const repository = document.querySelector("#repository");
const loadButton = document.querySelector("#load-button");
const question = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const form = document.querySelector("#chat-form");
const messages = document.querySelector("#messages");
const status = document.querySelector("#status");
const repoCard = document.querySelector("#repo-card");
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
  if (!value) return;
  loadButton.disabled = true;
  status.textContent = "Loading repository files...";
  try {
    const response = await fetch("/api/repository", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repository: value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load repository");
    loadedRepository = value;
    repoCard.classList.remove("hidden");
    repoCard.innerHTML = `<strong>${data.repository.full_name}</strong><span>${data.repository.description || "No description"}<br>${data.file_count.toLocaleString()} files · ${data.loaded_files.length} files loaded for chat</span>`;
    status.textContent = "Repository loaded. Ask a question.";
    question.disabled = false; sendButton.disabled = false; question.focus();
  } catch (error) {
    status.textContent = error.message;
  } finally { loadButton.disabled = false; }
}

loadButton.addEventListener("click", loadRepo);
repository.addEventListener("keydown", event => { if (event.key === "Enter") loadRepo(); });
document.querySelectorAll(".suggestions button").forEach(button => button.addEventListener("click", () => {
  question.value = button.textContent; question.focus();
}));
form.addEventListener("submit", async event => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text || !loadedRepository) return;
  addMessage("user", text); question.value = ""; question.disabled = true; sendButton.disabled = true; status.textContent = "Thinking...";
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repository: loadedRepository, question: text})
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Unable to answer");
    }
    const assistantBubble = addMessage("assistant", "", true);
    if (!response.body) {
      throw new Error("Streaming is not supported by this browser.");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let answer = "";
    let done = false;
    while (!done) {
      const result = await reader.read();
      done = result.done;
      buffer += decoder.decode(result.value || new Uint8Array(), {stream: !done});
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const event of events) {
        const line = event.split("\n").find(item => item.startsWith("data:"));
        if (!line) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload === "[DONE]") continue;
        if (payload.error) throw new Error(payload.error);
        answer += payload.text || "";
        assistantBubble.innerHTML = renderMarkdown(answer);
        messages.scrollTop = messages.scrollHeight;
      }
    }
    status.textContent = "Ready for another question.";
  } catch (error) {
    addMessage("assistant", `I couldn't answer that: ${error.message}`);
    status.textContent = "Request failed.";
  }
  finally { question.disabled = false; sendButton.disabled = false; question.focus(); }
});
