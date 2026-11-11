// The workbench page, for the student. The assignment's parts, each with a sentence or two on what
// it is for, and under each its steps (0a, 0b, ...), each with its summary under its title,
// open or closed. A step opens the same way for every step (left: any text before the first label
// of its instructions, then Tasks, then each labeled part of its instructions folded, to open on
// a click), and their record of working on it with Claude (right: what they
// expected, what they asked, what Claude ran and what came back, ending on the open question),
// with links to what the step produced and the command that opens its Claude Code session.
// The record shows what happened, never the next move. A setup step's tasks are numbered.
// The current step starts open; every other step shows its summary and every other part its
// description. The page polls the local server; nothing here talks to Claude. At the top, the
// notices: an update to the homework (with its Update button), a push that didn't go through, a
// folder that isn't the student's own fork. When the steps file or the brief's pages change, the
// page rebuilds itself.

const $ = (s, el = document) => el.querySelector(s);
const byId = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// A task, a question or a record line as the steps file or the write-up writes it: plain text,
// escaped first, except that *italic* and **bold** show as such, a `code` span as code, and a
// [link](address) as a link in a new tab when the address starts with https://, http:// or one /
// (a page of this homework page, such as /claims/). Any other link shows as its words. Nothing
// else in the text can become markup.
const WEB = /^(https?:\/\/|\/(?!\/))/;
const linkText = (t) => t.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,
  (m, words, href) => (WEB.test(href) ? `<a href="${href}" target="_blank" rel="noopener">${words}</a>` : words));
const emphasis = (t) => t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
  .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
const codeText = (s) => String(s ?? "").split(/(`[^`]+`)/)
  .map((part, i) => (i % 2 ? `<code>${esc(part.slice(1, -1))}</code>` : linkText(emphasis(esc(part))))).join("");

let A = null;               // the assignment
let S = null;               // the latest /api/state
const SESS = {};            // step id -> its latest /api/session snapshot
const openParts = new Set(), openSteps = new Set();
const detailSteps = new Set();   // steps whose record shows every message and command

// ---- a small Markdown renderer for the brief's text: headings, lists, code, tables, emphasis ----
function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|\/(?!\/)[^)\s]*)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, "$1");
}
function md(text) {
  const lines = String(text || "").split("\n");
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^\s*```/.test(l)) {
      const buf = []; i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) buf.push(lines[i++].replace(/^ {2,4}/, ""));
      i++; out.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`); continue;
    }
    const h = l.match(/^(#{1,4})\s+(.*)/);
    if (h) { out.push(`<h4>${inline(h[2])}</h4>`); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const body = rows.filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r));
      out.push("<table>" + body.map((r, k) => "<tr>" + cells(r).map((c) => k ? `<td>${inline(c)}</td>` : `<th>${inline(c)}</th>`).join("") + "</tr>").join("") + "</table>");
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      let html = ""; const stack = [];
      while (i < lines.length && !/^\s*```/.test(lines[i]) && (/^\s*([-*]|\d+\.)\s+/.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && stack.length))) {
        const m = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)/);
        if (!m) { html += " " + inline(lines[i].trim()); i++; continue; }
        const ind = m[1].length, tag = /\d/.test(m[2]) ? "ol" : "ul";
        while (stack.length && ind < stack[stack.length - 1].ind) html += `</li></${stack.pop().tag}>`;
        if (!stack.length || ind > stack[stack.length - 1].ind) { html += `<${tag}>`; stack.push({ ind, tag }); }
        else html += "</li>";
        html += `<li>${inline(m[3])}`; i++;
      }
      while (stack.length) html += `</li></${stack.pop().tag}>`;
      out.push(html); continue;
    }
    if (/^>\s?/.test(l)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`); continue;
    }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#|\s*```|\s*[-*]\s|\s*\d+\.\s|\s*\||>)/.test(lines[i])) buf.push(lines[i++]);
    if (!buf.length) buf.push(lines[i++]);
    out.push(`<p>${inline(buf.join(" "))}</p>`);
  }
  return out.join("\n");
}

// A step's instructions in order: the open text before the first label, then each labeled part. A
// labeled part is the paragraph that starts with a bold label ("**Actions:**"), the rest of its first
// line included, and everything after it up to the next paragraph that starts with a bold label or
// the end of the text. A label inside a code block is only text.
const LABEL_LINE = /^\*\*([^*]+):\*\*\s*(.*)$/;
function sections(text) {
  const lines = String(text || "").split("\n"), out = [];
  let cur = { label: null, lines: [] }, fence = false;
  lines.forEach((l, i) => {
    if (/^\s*```/.test(l)) fence = !fence;
    const m = !fence && (i === 0 || !lines[i - 1].trim()) ? l.match(LABEL_LINE) : null;
    if (m) { out.push(cur); cur = { label: m[1], lines: [m[2]] }; } else cur.lines.push(l);
  });
  out.push(cur);
  return out.map((x) => ({ label: x.label, text: x.lines.join("\n").trim() })).filter((x) => x.label || x.text);
}

// A step's instructions without their first paragraph when it repeats the summary shown under the
// step's title (compared with the whitespace collapsed). If it differs in any way, it stays.
const flat = (t) => String(t || "").split(/\s+/).join(" ").trim();
function withoutSummary(body, summary) {
  const text = String(body || "").replace(/^\s+/, "");
  const cut = text.search(/\n\s*\n/);
  const first = cut < 0 ? text : text.slice(0, cut);
  if (!flat(summary) || flat(first) !== flat(summary)) return String(body || "");
  return cut < 0 ? "" : text.slice(cut).replace(/^\s+/, "");
}

// Replace an element's HTML only when it changed, so polling keeps the student's place.
function paint(el, html) {
  if (!el || el._html === html) return false;
  el.innerHTML = html; el._html = html;
  return true;
}

async function get(path) { const r = await fetch(path); return r.json(); }

// ---- small helpers -------------------------------------------------------------------------
const stepOf = (id) => A.steps.find((s) => s.id === id);
const infoOf = (id) => S.steps.find((x) => x.id === id);
const labelOf = (id) => stepOf(id)?.label || id;
const due = (p) => String(p?.due || "").replace(/ \[TBD\]/, "");
const shortDue = (p) => due(p).replace(/^\d{1,2}:\d{2}(am|pm) /, "");
// The due date. When every part has the same one, it is said once, at the top, and no part repeats
// it. When the parts differ, each part's header gives its own, and the top line gives the current
// part's, as before.
function dueText(parts, part) {
  const all = parts.map(due);
  const same = all.length > 0 && !!all[0] && all.every((d) => d === all[0]);
  return { same, top: same ? `Everything is due ${all[0]}.`
    : part?.due ? `Part ${part.number}${part.extra_credit ? " (extra credit)" : ""} is due ${due(part)}` : "" };
}
const rel = (path) => (path && path.startsWith(A.repo + "/") ? path.slice(A.repo.length + 1) : path);
const trim = (t, n) => { t = String(t || "").replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n - 1) + "…" : t; };

function stepClass(st) {
  if (st.complete) return "done";
  if (st.id === S.now) return "current";
  return st.locked ? "locked" : "ready";
}
function badge(st) {
  if (st.complete) return '<span class="badge done">Done</span>';
  if (st.id === S.now) return '<span class="badge turn">Your turn</span>';
  if (st.locked) return `<span class="badge">Opens after ${st.waiting_on.map(labelOf).join(", ")}</span>`;
  return '<span class="badge">Ready</span>';
}

// ---- the skeleton: parts and steps, built once ----------------------------------------------
function build() {
  const [course] = A.title.split(":");
  byId("course").textContent = A.title.includes(":") ? course : "";
  byId("title").textContent = A.title.includes(":") ? A.title.slice(A.title.indexOf(":") + 1).trim() : A.title;
  document.title = A.title;
  byId("lede").textContent = A.lede || "";
  // The learning goals, from README's bullets after its first paragraph; nothing if it has none.
  paint(byId("goals"), A.goals && A.goals.length
    ? `<p>You will:</p><ul>${A.goals.map((g) => `<li>${inline(g)}</li>`).join("")}</ul>` : "");
  byId("parts").innerHTML = A.parts.map((p) => `
    <section class="part" id="part-${p.number}">
      <button class="part-head" data-part="${p.number}" aria-expanded="false" aria-controls="steps-${p.number}" type="button">
        <span class="part-title"><span class="no">Part ${p.number}${p.extra_credit ? " (extra credit)" : ""}</span>${esc(p.title)}</span>
        <span class="part-meta nums" id="meta-${p.number}"></span><span class="chev"></span></button>
      ${p.desc ? `<p class="part-desc">${esc(p.desc)}</p>` : ""}
      <ol class="steps" id="steps-${p.number}" hidden>${A.steps.filter((s) => s.part === p.number).map((s) => `
        <li class="step" id="step-${s.label}">
          <button class="step-head" data-step="${s.id}" aria-expanded="false" aria-controls="body-${s.label}" type="button">
            <span class="dot"></span>
            <span class="step-title"><span class="id">${esc(s.label)}</span>${esc(s.title)}${minutes(s)}</span>
            <span class="badge-slot" id="badge-${s.label}"></span><span class="chev"></span></button>
          ${s.summary ? `<p class="step-sum">${esc(s.summary)}</p>` : ""}
          <div class="step-body" id="body-${s.label}" hidden>
            <div class="col">${leftCol(s)}</div>
            <div class="col record" id="pg-${s.label}"></div>
          </div></li>`).join("")}</ol>
    </section>`).join("");
}

// How long a step takes, in plain words, when the steps file says.
function minutes(s) {
  const m = Number(s.minutes);
  return m > 0 ? `<span class="mins">about ${m} minute${m === 1 ? "" : "s"}</span>` : "";
}

// An open step's left column, the same for every step: the text before the first label (the
// summary already under the title is left out; the claim box only when that text does not quote
// the claim), then Tasks, then every labeled part of the instructions folded, in their order. Each
// fold has a key (the step, its place and its label), so one the student opened stays open if the
// page rebuilds itself.
function leftCol(s) {
  const secs = sections(withoutSummary(s.body, s.summary));
  const first = secs.length && !secs[0].label ? secs.shift().text : "";
  const claim = s.claim && A.sample_claim && !flat(first).includes(flat(A.sample_claim))
    ? `<div class="claimbox">${esc(A.sample_claim)}</div>` : "";
  return claim + (first ? `<div class="doc opening">${md(first)}</div>` : "")
    + `<div class="counts" id="dw-${s.label}"></div>`
    + (secs.length ? `<div class="doc folds">${secs.map((x, n) =>
        `<details class="fold" data-key="${esc(s.label)}:${n}:${esc(x.label)}"><summary>${esc(x.label)}</summary>`
        + `<div class="fold-body">${md(x.text)}</div></details>`).join("")}</div>` : "");
}

// ---- what changes: progress, state, the open steps -------------------------------------------
// What the top of the page tells the student: one plain sentence each, and the Update button.
function notices() {
  return (S.notices || []).map((x) => `<div class="notice ${esc(x.kind)}"><p>${esc(x.text)}</p>`
    + (x.items ? `<ul>${x.items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : "")
    + (x.code ? `<pre><code>${esc(x.code)}</code></pre>` : "")
    + (x.button ? `<button class="copy" data-update type="button">${esc(x.button)}</button>` : "")
    + "</div>").join("");
}

function update() {
  if (!byId("notices").querySelector("[data-update][disabled]")) paint(byId("notices"), notices());
  // The count is of the required steps; a part marked extra credit is said so, and not counted.
  const extra = A.parts.filter((p) => p.extra_credit).map((p) => p.number);
  const required = S.steps.filter((x) => !extra.includes(x.part));
  const n = required.filter((x) => x.complete).length;
  byId("bar").style.width = `${(100 * n / Math.max(1, required.length)).toFixed(1)}%`;
  byId("count").textContent = `${n} of ${required.length} steps done`
    + (extra.length ? `. Part ${extra.join(" and Part ")} ${extra.length > 1 ? "are" : "is"} extra credit.` : "");
  // Once the required steps are done, the next open step is extra credit, and the page says so.
  const now = S.now && stepOf(S.now);
  const part = now && A.parts.find((p) => p.number === now.part);
  const jump = now ? `<a href="#step-${now.label}" id="jump">${esc(now.label)}, ${esc(now.title)}</a>` : "";
  paint(byId("next"), !now ? "Every step is done."
    : part?.extra_credit && n === required.length ? `Every required step is done. The next step, ${jump}, is extra credit.`
    : `Now: ${jump}`);
  const dues = dueText(A.parts, part);
  byId("due").textContent = dues.top;

  for (const p of A.parts) {
    const mine = S.steps.filter((x) => x.part === p.number), done = mine.filter((x) => x.complete).length;
    const saved = S.committed.includes(p.number);
    const pushed = S.push && S.push.on && S.push.ok ? " and pushed to GitHub" : "";
    byId(`meta-${p.number}`).textContent = (saved ? `Committed as “Part ${p.number} done”${pushed}` : done ? `${done} of ${mine.length} done` : `${mine.length} steps`)
      + (p.due && !saved && !dues.same ? ` · due ${shortDue(p)}` : "");
    const open = openParts.has(p.number);
    $(`[data-part="${p.number}"]`).setAttribute("aria-expanded", String(open));
    byId(`steps-${p.number}`).hidden = !open;
  }
  for (const s of A.steps) {
    const st = infoOf(s.id), open = openSteps.has(s.id), li = byId(`step-${s.label}`);
    li.className = `step ${stepClass(st)}${open ? " open" : ""}`;
    $(".dot", li).textContent = st.complete ? "✓" : "";
    paint(byId(`badge-${s.label}`), badge(st));
    $(".step-head", li).setAttribute("aria-expanded", String(open));
    byId(`body-${s.label}`).hidden = !open;
    if (open && SESS[s.id]) {
      paint(byId(`dw-${s.label}`), counts(s, st, SESS[s.id].record, SESS[s.id].started));
      paint(byId(`pg-${s.label}`), recordCol(s, st, SESS[s.id]));
    }
  }
}

// Tasks: the step's checkpoints. One that the student's answers complete shows each question
// and their answer; the rest show their task, a full sentence saying what to do. A setup step
// shows every task, numbered, each with its tick (and the student's answer under one they answer).
// The list begins with when to start the step's Claude session, ticked once it has started, and
// ends with when to stop it. The page cannot see /exit, so that last task has no tick.
function counts(s, st, rec, started) {
  const row = (ok, text, sub, mine) => `<div class="check ${ok ? "ok" : ""}"><span class="tick">${ok ? "✓" : "○"}</span>
      <div><span class="q">${codeText(text)}</span>${sub ? `<div class="ans ${mine ? "mine" : ""}">${esc(sub)}</div>` : ""}</div></div>`;
  const noTick = (text) => `<div class="check"><span class="tick"></span><div><span class="q">${codeText(text)}</span></div></div>`;
  const ask = s.session_tasks || {}, numbered = rec.checkpoints.filter((c) => c.n).length;
  const rows = s.setup ? rec.checkpoints.filter((c) => c.n).map((c) => row(c.done, `${c.n}. ${c.task || c.text}`,
      c.slots.length && c.slots.every((x) => x.filled) ? c.slots.map((x) => trim(x.answer, 200)).join(", ") : "", true))
    : rec.checkpoints.flatMap((c) => c.slots.length
    ? c.slots.map((x) => row(x.filled, x.question.replace(/^Table: /, "The table: "),
        x.filled ? trim(x.answer, 400) : (x.todo || `Not written yet. Type it in WRITEUP.md, under ${s.label}.`), x.filled))
    : [row(c.done, c.task || c.text, c.files.join(", "), false)]);
  if (!rows.length && st.manual) rows.push(row(st.complete, "Claude ticks this step once you have done what it asks.", "", false));
  if (ask.start) rows.unshift(row(started, ask.start, "", false));
  if (ask.stop) rows.push(noTick(s.setup ? `${numbered + 1}. ${ask.stop}` : ask.stop));
  return rows.length ? `<span class="label">Tasks</span>${rows.join("")}` : "";
}

function stateLine(ss) {
  const lastYou = Math.max(0, ...ss.events.filter((e) => e.kind === "student").map((e) => e.t));
  if (ss.state === "asking") return "Claude is asking your permission in the terminal.";
  if (ss.status && ss.status.t > lastYou) return ss.status.text + ".";
  if (ss.state === "your turn") return "Claude is waiting for you in the terminal. It does nothing until you tell it to.";
  if (ss.state === "working") return `Claude is working: ${ss.now}.`;
  if (ss.state === "thinking") return "Claude is thinking.";
  return ss.now || "";
}

function fileLink(path, text) {
  return `<button class="linkbtn" data-file="${esc(path)}" type="button">${esc(text || path)}</button>`;
}

// The record, read top to bottom as plain sentences in one style: a tick for a checkpoint reached, a
// dot for anything else, a circle for the open question. By default only the step's milestones
// (checkpoints reached, what the student predicted, what came back); one click shows every
// message and command, and the conversation link has the whole transcript.
const line = (mark, html) => `<li class="ln ${mark}"><span class="mk"></span><span>${html}</span></li>`;
const ink = (t) => `<span class="ink">${esc(t)}</span>`;
const after = (n) => n === null || n === undefined ? "" : n === 0 ? ", with no lookups" : `, after ${n} lookup${n === 1 ? "" : "s"}`;

function recordSummary(rec) {
  return rec.summary.flatMap((x) => {
    if (x.kind === "predicted") return [line("plain", `You predicted ${ink(x.text)}.`)];
    if (x.kind === "result") return [line("plain", `It said ${ink(x.verdict)}${after(x.lookups)}.${x.file ? " " + fileLink(x.file, "See the output.") : ""}`),
      ...(x.reached || []).map((t) => line("tick", codeText(t) + "."))];
    if (x.kind === "reached") return [line("tick", codeText(x.text) + ".")];
    return [];
  });
}

// "Ran check.py" reads as "Claude ran check.py"; a command known only by its description, such as
// "Find the claim", reads as "Claude ran a command to find the claim".
function claudeDid(label) {
  const lower = label.replace(/^(\w)/, (c) => c.toLowerCase());
  return /^(Ran|Read|Edited|Searched|Listed|Looked|Installed|Committed|Pushed|Checked|Updated|Used|Fetched|Refused)\b/.test(label)
    ? `Claude ${esc(lower)}` : `Claude ran a command to ${esc(lower)}`;
}

function recordDetail(rec) {
  return rec.entries.flatMap((x) => {
    const out = [];
    if (x.kind === "expected") out.push(line("plain", `You predicted: ${ink("“" + trim(x.text || x.verdict, 300) + "”")}`));
    if (x.kind === "asked") out.push(line("plain", `You said: ${ink("“" + trim(x.text, 300) + "”")}`));
    if (x.kind === "ran") out.push(line("plain", `${claudeDid(x.text)}${x.status === "error" ? ", and it failed" : ""}.`));
    if (x.kind === "said") out.push(line("plain", `It said ${ink(x.verdict)}${after(x.lookups)}.${x.reason ? ` Its reason: ${esc(trim(x.reason, 300))}` : ""}`));
    (x.reached || []).forEach((t) => out.push(line("tick", codeText(t) + ".")));
    return out;
  });
}

function recordList(s, rec) {
  const detail = detailSteps.has(s.id);
  const items = detail ? recordDetail(rec) : recordSummary(rec);
  const now = rec.now;
  if (now.plain) items.push(line("ring", `Now: <strong class="ink">${codeText(now.plain)}</strong>`));
  else if (now.question) items.push(line("ring", `Now: <strong class="ink">${codeText(now.question)}</strong> ${esc(now.how)}`));
  else if (now.todo) items.push(line("ring", `Still to do: <span class="ink">${codeText(now.todo)}</span>`));
  else items.push(line("tick", "This step is done."));
  const c = rec.counts, n = (k, w) => `${k} ${w}${k === 1 ? "" : "s"}`;
  const toggle = c.messages || c.commands
    ? `<button class="linkbtn" data-detail="${s.id}" type="button">${detail ? "Show only the checkpoints and results" : `Show every message and command (${n(c.messages, "message")}, ${n(c.commands, "command")})`}</button>` : "";
  return (detail && rec.earlier ? `<p>The conversation has ${rec.earlier} earlier lines.</p>` : "")
    + `<ul class="lines">${items.join("")}</ul>${toggle}`;
}

function links(s, ss) {
  const files = new Set();
  for (const e of ss.events) {
    if (e.kind === "tool" && (e.category === "read" || e.category === "write") && e.detail) {
      const r = rel(e.detail);
      if (r && !r.startsWith("/") && !r.startsWith(".workbench") && r !== "WRITEUP.md") files.add(r);
    }
  }
  ss.record.entries.forEach((x) => x.file && files.add(x.file));
  ss.record.checkpoints.forEach((c) => c.files.forEach((f) => files.add(f)));
  const items = [`<li><button class="linkbtn" data-convo="${s.id}" type="button">The conversation</button></li>`,
    ...(ss.results ? [`<li>${resultsLink(ss)}</li>`] : []),
    `<li>${fileLink("WRITEUP.md")}</li>`, ...[...files].slice(0, 6).map((f) => `<li>${fileLink(f)}</li>`)];
  return `<div class="files"><span class="label">From this step</span><ul>${items.join("")}</ul></div>`;   // one row of links
}

// The step's results in the results viewer, which decides what to show for the file.
function resultsLink(ss) {
  return `<a href="/results/open?path=${encodeURIComponent(ss.results)}" target="_blank" rel="noopener">Open these results</a>`;
}

function command(label, cmd) {
  return `<div class="cmd"><span class="label">${label}</span>
    <div class="cmd-row"><code title="${esc(cmd)}">${esc(cmd)}</code><button class="copy" data-copy="${esc(cmd)}" type="button">Copy</button></div>
    <span class="small">Paste this into a terminal in your homework folder, not into a Claude chat. If the last step's Claude is still open in that terminal, type /exit first.</span></div>`;
}

// A command the student runs in a terminal tab of their own (a long run), under the Claude command.
function yourself(s) {
  const r = s.run_yourself;
  if (!r) return "";
  return `<div class="cmd"><span class="label">Run this yourself, in a terminal tab of your own</span>
    <div class="cmd-row"><code title="${esc(r.command)}">${esc(r.command)}</code><button class="copy" data-copy="${esc(r.command)}" type="button">Copy</button></div>
    ${r.note ? `<span class="small">${esc(r.note)}</span>` : ""}</div>`;
}

function recordCol(s, st, ss) {
  const when = st.waiting_on.map(labelOf).join(", ");
  const cmd = ss.command ? command(ss.started ? "Back to this conversation" : "Start this step's Claude", ss.command)
    + yourself(s) : "";
  if (!ss.started) {
    const state = st.locked ? `This record is empty. This step's Claude opens when you finish ${when}.`
      : "This record is empty. Start this step's Claude in a terminal.";
    return `<div class="record-head"><span class="label">Your record</span><span class="state">${esc(state)} What you ask Claude, and what comes back, will be recorded here.</span></div>${ss.results ? `<p class="small">${resultsLink(ss)}</p>` : ""}${cmd}`;
  }
  return `<div class="record-head"><span class="label">Your record</span><span class="state">${esc(stateLine(ss))}</span></div>
    ${recordList(s, ss.record)}${links(s, ss)}${cmd}`;
}

// ---- the panel a link opens: the conversation, or a file --------------------------------------
let lastFocus = null;
function showPanel(title, html, from) {
  byId("panel-title").textContent = title;
  byId("panel-body").innerHTML = html;
  byId("panel").hidden = false; byId("scrim").hidden = false;
  lastFocus = from; byId("panel-close").focus();
}
function closePanel() {
  byId("panel").hidden = true; byId("scrim").hidden = true;
  if (lastFocus) lastFocus.focus();
}
function conversation(ss) {
  return ss.events.map((e) => {
    if (e.kind === "student" && e.opening) return `<span class="note">Started in the terminal with “${esc(e.text)}”</span>`;
    if (e.kind === "student") return `<div class="msg you"><span class="label">You</span>${md(e.text)}</div>`;
    if (e.kind === "claude") return `<div class="msg claude"><span class="label">Claude</span>${md(e.text)}</div>`;
    if (e.kind === "tool") return `<p class="tool">Claude ${esc(e.label.replace(/^(\w)/, (c) => c.toLowerCase()))}${e.detail ? `: <code>${esc(trim(e.detail, 160))}</code>` : ""}</p>`;
    if (e.kind === "note") return `<span class="note">${esc(e.text)}</span>`;
    if (e.kind === "permission") return `<span class="note">Claude asked your permission in the terminal: ${esc(e.label)}</span>`;
    return "";
  }).join("") || '<p class="small">Nothing yet.</p>';
}

// ---- wiring ----------------------------------------------------------------------------------
document.addEventListener("click", async (ev) => {
  const part = ev.target.closest("[data-part]");
  if (part) { const n = +part.dataset.part; openParts.has(n) ? openParts.delete(n) : openParts.add(n); update(); return; }
  const step = ev.target.closest("[data-step]");
  if (step) {
    const id = step.dataset.step;
    if (openSteps.has(id)) openSteps.delete(id); else { openSteps.add(id); await pollStep(id); }
    update(); return;
  }
  if (ev.target.id === "jump") { ev.preventDefault(); return goNow(); }
  const detail = ev.target.closest("[data-detail]");
  if (detail) { const id = detail.dataset.detail; detailSteps.has(id) ? detailSteps.delete(id) : detailSteps.add(id); update(); return; }
  const convo = ev.target.closest("[data-convo]");
  if (convo) { const id = convo.dataset.convo; await pollStep(id); return showPanel(`${labelOf(id)}: the conversation`, conversation(SESS[id]), convo); }
  const file = ev.target.closest("[data-file]");
  if (file) {
    const r = await get(`/api/file?path=${encodeURIComponent(file.dataset.file)}`);
    return showPanel(file.dataset.file, r.error ? `<p class="small">${esc(r.error)}</p>`
      : `<pre class="file">${esc(r.text)}</pre>${r.cut ? '<p class="small">The file is longer; this is its start.</p>' : ""}`, file);
  }
  const upd = ev.target.closest("[data-update]");
  if (upd) {
    upd.disabled = true; upd.textContent = "Updating…";
    try { await fetch("/api/update", { method: "POST" }); } catch (_) { /* the notices say what happened */ }
    upd.disabled = false;
    return refresh();
  }
  const copy = ev.target.closest("[data-copy]");
  if (copy) {
    try { await navigator.clipboard.writeText(copy.dataset.copy); copy.textContent = "Copied"; }
    catch (_) {
      const code = copy.parentElement.querySelector("code"), r = document.createRange();
      r.selectNodeContents(code); getSelection().removeAllRanges(); getSelection().addRange(r); copy.textContent = "Selected";
    }
    setTimeout(() => { copy.textContent = "Copy"; }, 1500);
  }
});
byId("panel-close").addEventListener("click", closePanel);
byId("scrim").addEventListener("click", closePanel);
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !byId("panel").hidden) closePanel(); });

function goNow() {
  const s = S.now && stepOf(S.now);
  if (!s) return;
  openParts.add(s.part); openSteps.add(s.id);
  pollStep(s.id).then(() => { update(); byId(`step-${s.label}`).scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); });
}

async function pollStep(id) { SESS[id] = await get(`/api/session/${id}`); }
async function refresh() {
  S = await get("/api/state");
  if (S.version !== A.version) {   // the steps file or a page changed: rebuild, keeping what is open
    A = await get("/api/assignment");
    for (const id of [...openSteps]) if (!stepOf(id)) openSteps.delete(id);
    const keep = new Set([...byId("parts").querySelectorAll("details[open][data-key]")].map((d) => d.dataset.key));
    build();
    for (const d of byId("parts").querySelectorAll("details[data-key]")) if (keep.has(d.dataset.key)) d.open = true;
  }
  await Promise.all([...openSteps].map(pollStep));
  update();
}

(async function boot() {
  A = await get("/api/assignment");
  S = await get("/api/state");
  build();
  const first = S.now ? stepOf(S.now) : null;
  if (first) { openParts.add(first.part); openSteps.add(first.id); await pollStep(first.id); }
  else if (A.parts.length) openParts.add(A.parts[0].number);
  update();
  setInterval(refresh, 2000);
})();
