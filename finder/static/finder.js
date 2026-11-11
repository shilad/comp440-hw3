// The claim finder's screen. The student searches one topic at a time, reads down the results and
// selects the claims they want, until they have 112. The server searches and saves (finder/web.py);
// this file shows the results and keeps the selection in the browser's own storage, so that a
// reload or another search does not lose it.
"use strict";

const byId = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// HoVer writes some article titles with HTML codes ("Percy Jackson &amp; the Olympians"); show them plainly.
const plain = (s) => new DOMParser().parseFromString(String(s ?? ""), "text/html").documentElement.textContent;
const LABEL = { SUPPORTED: "supported", NOT_SUPPORTED: "not supported" };
const NUMBER = { 2: "two", 3: "three", 4: "four" };
const HELP = "If this happens again, post in #comp440-f26 on Slack.";
const NEEDED = 112;     // the claims a student saves: 12 development claims and 100 evaluation claims
// A topic is thin when fewer claims than this contain all of its words. The number comes from
// measuring 19 topics: below about 200 such claims, the end of the list was mostly off the topic.
const FEW_CLAIMS = 200;
const KEY = "comp440-hw3-claim-finder-selection";   // where the browser keeps the selection
const REMOVED_KEY = "comp440-hw3-claim-finder-removed";   // and the ids of the claims the student removed

const selection = new Map(stored(KEY).map((c) => [c.id, c]));   // id -> claim, with "query": the search that found it
// The claims the student took out of the selection with Remove. "Select all shown" leaves them out;
// only a claim's own Select brings it back.
const removed = new Set(stored(REMOVED_KEY));
const shown = new Map();               // id -> claim, for the search results on the screen
let current = null;                    // the last search: its query, way of searching and total
let asked = 0;                         // counts searches, so an answer that arrives late is ignored

const claims = (n) => `${n} ${n === 1 ? "claim" : "claims"}`;
const contain = (n) => `${claims(n)} ${n === 1 ? "contains" : "contain"}`;

function stored(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch (err) {
    return [];
  }
}

function keep() {
  try {
    localStorage.setItem(KEY, JSON.stringify([...selection.values()]));
    localStorage.setItem(REMOVED_KEY, JSON.stringify([...removed]));
  } catch (err) {
    say("This browser does not let the page store your selection, so do not reload the page before you save.", true);
  }
}

function say(text, failed = false) {
  byId("said").textContent = text;
  byId("said").className = failed ? "failed" : "";
}

function how() {
  return document.querySelector('input[name="how"]:checked').value;
}

// ---- searching -------------------------------------------------------------------------------

// A new search, or with `more` the next 50 results of the last one.
async function search(more = false) {
  const query = more ? current.query : byId("q").value.trim();
  const way = more ? current.how : how();
  if (!query) {
    byId("status").textContent = "Type a few words about your topic first.";
    return;
  }
  const mine = ++asked;
  byId("status").textContent = mine === 1
    ? "Searching. The first search takes a few seconds, because the claims are loaded then."
    : "Searching.";
  byId("all-said").textContent = "";
  const start = more ? shown.size : 0;
  let answer;
  try {
    const r = await fetch("/claims/search?" + new URLSearchParams({ q: query, how: way, start: start }));
    answer = r.ok ? await r.json() : { error: await r.text() };
  } catch (err) {
    answer = { error: "The homework page did not answer. Check that it is still running in its terminal." };
  }
  if (mine !== asked) return;      // a newer search has started
  if (answer.error) {
    byId("status").textContent = answer.error + " " + HELP;
    return;
  }
  if (!more) {
    current = { query: answer.query, how: answer.how, total: answer.total };
    shown.clear();
    byId("results").innerHTML = "";
    byId("matches").textContent = answer.total ? matchesText(answer) : "";
  }
  answer.results.forEach((c) => shown.set(c.id, c));
  byId("results").insertAdjacentHTML("beforeend", answer.results.map((c) => cardHtml(c, false)).join(""));
  byId("status").textContent = answer.total ? "" : "Nothing matches these words. Try other words, or another way of searching.";
  byId("more-row").hidden = shown.size >= answer.total;
  byId("shown").textContent = `These are the first ${shown.size} of the ${answer.total} claims this search found.`;
  byId("above").hidden = shown.size === 0;
  allButton();
}

// How many claims contain all of the student's words, and a calm warning when that is few. For a
// description of several words, no claim containing all of them is usual and says nothing about
// the topic. (A one-word search that no claim contains finds nothing by keyword, and the screen
// then says "Nothing matches these words." instead.)
function matchesText(answer) {
  const all = answer.matches.all;
  const severalWords = answer.query.trim().split(/\s+/).length > 1;
  if (all === 0 && severalWords) {
    return "No claim contains all of your words, which is usual for a description of several words. " +
      "Read down the list, and select the claims that are on your topic.";
  }
  if (all === 0) {
    return "No claim contains your word, so the claims below were found by meaning alone and may be off your topic.";
  }
  if (all < FEW_CLAIMS) {
    return `Only ${contain(all)} all of your words, so further down, the list may stop being about your topic. ` +
      "Select the ones that are on your topic, and search another topic for the rest.";
  }
  return `${contain(all)} all of your words.`;
}

// ---- one claim ---------------------------------------------------------------------------------

// A claim as a card: in the search results with its ranks, or in the selection with its search.
function cardHtml(c, inSelection) {
  const chosen = selection.has(c.id);
  const articles = c.articles.map((title, i) => {
    const about = (c.about || [])[i];
    return `<li><span class="ink">${esc(plain(title))}</span>${about ? ", " + esc(about) : ""}</li>`;
  }).join("");
  const found = inSelection ? `It was found by your search for “${esc(c.query)}”.` : rankText(c);
  return `<li class="claim${chosen ? " chosen" : ""}" data-id="${esc(c.id)}">
    <div class="body">
      <p class="mark">You have selected this claim.</p>
      <p class="text">${esc(c.claim)}</p>
      <p>The dataset's label is ${LABEL[c.label] || esc(c.label)}, and the claim needs ${NUMBER[c.hops] || esc(c.hops)} articles.</p>
      <ul class="articles">${articles}</ul>
      <p class="found">${found}</p>
    </div>
    <button class="pick" type="button" data-toggle="${esc(c.id)}">${chosen ? "Remove" : "Select"}</button>
  </li>`;
}

// The claim's rank in each search (1 is best); a search that did not find it gives no rank.
function rankText(c) {
  const k = c.keyword_rank, m = c.meaning_rank;
  if (k && m) return `Its rank is ${k} by keyword and ${m} by meaning.`;
  if (k) return `Its rank is ${k} by keyword. The search by meaning did not put it among its best 1,000.`;
  if (m) return `Its rank is ${m} by meaning. It contains none of your words, so the search by keyword did not find it.`;
  return "";
}

// ---- the selection -------------------------------------------------------------------------------

function toggle(id) {
  if (selection.has(id)) {
    selection.delete(id);
    removed.add(id);
  } else {
    selection.set(id, { ...shown.get(id), query: current.query });
    removed.delete(id);
  }
  keep();
  paint(id);
  tally();
  allButton();
  byId("all-said").textContent = "";
  if (!byId("mine").hidden) drawSelection();
}

// Show on every card of this claim whether it is selected.
function paint(id) {
  document.querySelectorAll(`.claim[data-id="${CSS.escape(id)}"]`).forEach((card) => {
    card.classList.toggle("chosen", selection.has(id));
    card.querySelector(".pick").textContent = selection.has(id) ? "Remove" : "Select";
  });
}

// ---- selecting every claim shown -------------------------------------------------------------------

// What "Select all shown" would select now: the claims shown that are neither selected nor removed
// by the student, from the top of the list, as many as there is room for under 112. `skipped` counts
// the claims shown that it leaves out because the student removed them.
function selectable() {
  const unselected = [...shown.values()].filter((c) => !selection.has(c.id));
  const left = unselected.filter((c) => !removed.has(c.id));
  return { left: left, take: left.slice(0, Math.max(0, NEEDED - selection.size)),
           skipped: unselected.length - left.length };
}

// The button's label says how many claims it would select. With none to select, it is disabled.
function allButton() {
  const { left, take } = selectable();
  byId("all").disabled = take.length === 0;
  byId("all").textContent = allLabel(left.length, take.length);
}

function allLabel(left, take) {
  if (take === 0) return "Select all shown";
  if (take < left) return take === 1 ? "Select the first one shown" : `Select the first ${take} shown`;
  return left === 1 ? "Select the 1 shown" : `Select all ${left} shown`;
}

// Select every claim shown that the student has not removed, each as if its own Select had been
// pressed, but never more than 112.
function selectAll() {
  const { left, take, skipped } = selectable();
  take.forEach((c) => selection.set(c.id, { ...c, query: current.query }));
  keep();
  take.forEach((c) => paint(c.id));
  tally();
  allButton();
  byId("all-said").textContent = allSentence(take.length, left.length, skipped);
}

// What the button did, in a sentence, and a second one when it left out claims the student removed.
function allSentence(took, left, skipped) {
  const more = `You selected ${took} more ${took === 1 ? "claim" : "claims"}`;
  const first = took === 1 ? "the first one" : `the first ${took}`;
  const text = took < left
    ? `${more}, ${first} in the list. You have ${selection.size}, which is all you need.`
    : `${more}. You have now selected ${selection.size} of ${NEEDED}.`;
  if (!skipped) return text;
  return text + (skipped === 1 ? " The claim you removed earlier stays removed."
                               : ` The ${skipped} claims you removed earlier stay removed.`);
}

// The line at the top: how many are selected, and of which label.
function tally() {
  const n = selection.size;
  const yes = [...selection.values()].filter((c) => c.label === "SUPPORTED").length;
  byId("count").textContent = `You have selected ${n} of ${NEEDED} claims: ${yes} supported and ${n - yes} not ` +
    "supported." + (n > NEEDED ? ` Remove ${n - NEEDED} before you save.` : "");
}

// The selected claims, grouped by the search that found them, in the order of those searches.
function drawSelection() {
  const groups = new Map();
  for (const c of selection.values()) groups.set(c.query, [...(groups.get(c.query) || []), c]);
  byId("groups").innerHTML = selection.size === 0 ? "<p>You have not selected any claims yet.</p>" :
    [...groups].map(([query, cs]) => `<h3>From your search for “${esc(query)}” you selected ${claims(cs.length)}.</h3>
      <ol class="claims">${cs.map((c) => cardHtml(c, true)).join("")}</ol>`).join("");
}

function showSelection(open) {
  byId("mine").hidden = !open;
  byId("searching").hidden = open;
  byId("toggle").textContent = open ? "Back to the search results" : "Show my selection";
  if (open) drawSelection();
  byId("tally").scrollIntoView();
}

// ---- saving ----------------------------------------------------------------------------------------

async function save() {
  say("Saving.");
  const selected = [...selection.values()].map((c) => ({ id: c.id, query: c.query }));
  let answer;
  try {
    const r = await fetch("/claims/save", { method: "POST", headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ selected: selected }) });
    answer = r.ok ? await r.json() : { ok: false, why: (await r.text()) + " " + HELP };
  } catch (err) {
    answer = { ok: false, why: "The homework page did not answer. Check that it is still running in its terminal." };
  }
  if (!answer.ok) {
    say(answer.why, true);
    return;
  }
  say(`Your ${answer.development} development claims are saved in data/dev.jsonl and your ${answer.evaluation} ` +
    "evaluation claims in data/eval.jsonl. Every run from step 1c on uses them.");
  showSaved(answer);
}

// The note at the top when claims are saved already.
function showSaved(s) {
  const box = byId("saved");
  box.hidden = !s.saved;
  if (!s.saved) return;
  box.classList.toggle("locked", Boolean(s.run));
  const topics = (s.topics || []).map((t) => `“${t}”`);
  const list = topics.length > 1 ? topics.slice(0, -1).join(", ") + " and " + topics[topics.length - 1] : topics[0];
  const found = topics.length ? `, found by your ${topics.length > 1 ? "searches" : "search"} for ${list}` : "";
  box.textContent = `You have saved ${s.development} development claims in data/dev.jsonl and ${s.evaluation} ` +
    `evaluation claims in data/eval.jsonl${found}. ` + (s.run
    ? "The agent has already run on them in step 1c or later, so saving here will not replace them."
    : "Saving again replaces them.");
}

async function loadSaved() {
  try {
    showSaved(await (await fetch("/claims/saved")).json());
  } catch (err) {
    // the note is a convenience; the screen works without it
  }
}

// ---- wiring --------------------------------------------------------------------------------------

byId("search").addEventListener("submit", (ev) => {
  ev.preventDefault();
  search();
});
document.querySelectorAll('input[name="how"]').forEach((el) => el.addEventListener("change", () => current && search()));
document.addEventListener("click", (ev) => {
  const id = ev.target.dataset && ev.target.dataset.toggle;
  if (id) toggle(id);
});
byId("more").addEventListener("click", () => search(true));
byId("all").addEventListener("click", selectAll);
byId("toggle").addEventListener("click", () => showSelection(byId("mine").hidden));
byId("save").addEventListener("click", save);

// /claims/?q=jazz+musicians&how=meaning opens the screen with that search done.
const start = new URLSearchParams(location.search);
if (["keyword", "meaning", "both"].includes(start.get("how"))) {
  document.querySelector(`input[name="how"][value="${start.get("how")}"]`).checked = true;
}
if (start.get("q")) {
  byId("q").value = start.get("q");
  search();
}
tally();
loadSaved();
