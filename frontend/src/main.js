import "./styles.css";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const API_BASE = configuredApiBase.replace(/\/+$/, "");

const form = document.querySelector("#prefs");
const submit = document.querySelector("#submit");
const rating = document.querySelector("#min_rating");
const ratingOut = document.querySelector("#rating-out");
const statusText = document.querySelector("#status-text");
const results = document.querySelector("#results");
const locality = document.querySelector("#locality");
const extras = document.querySelector("#extras");
const engineStatus = document.querySelector("#engine-status");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function fillDatalist(id, values) {
  const list = document.getElementById(id);
  list.replaceChildren(
    ...(values || []).map((value) => {
      const option = document.createElement("option");
      option.value = value;
      return option;
    }),
  );
}

function renderBudgetBands(bands) {
  if (!bands?.length) return;
  const selected = new FormData(form).get("budget") || "medium";
  const segments = document.querySelector("#budget-segments");
  segments.replaceChildren(
    ...bands.map((band) => {
      const label = element("label", "segment");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "budget";
      input.value = band.id;
      input.checked = band.id === selected;
      label.append(input, element("span", "", band.label));
      return label;
    }),
  );
}

async function loadMeta() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/metadata`);
    if (!response.ok) throw new Error(`Catalog returned ${response.status}`);
    const meta = await response.json();
    fillDatalist("locality-list", meta.localities);
    fillDatalist("cuisine-list", meta.cuisines);
    renderBudgetBands(meta.budget_bands);
    engineStatus.className = "pill pill--mint";
    engineStatus.replaceChildren(element("span", "dot dot--live"), `${meta.localities.length} verified localities`);
  } catch (error) {
    console.error("Could not load catalog metadata", error);
    engineStatus.className = "pill pill--error";
    engineStatus.textContent = "API unavailable";
    statusText.textContent = "The restaurant catalog is unavailable. Check the API connection.";
  }
}

function syncRating() {
  ratingOut.textContent = `Min ${Number(rating.value).toFixed(1)} ★`;
}

function autoGrow() {
  extras.style.height = "auto";
  extras.style.height = `${extras.scrollHeight}px`;
}

function showSkeletons() {
  results.replaceChildren();
  for (let index = 0; index < 3; index += 1) {
    const block = element("div", "skeleton");
    block.append(
      element("div", "skeleton__bar skeleton__bar--title"),
      element("div", "skeleton__bar skeleton__bar--wide"),
      element("div", "skeleton__bar skeleton__bar--mid"),
    );
    results.append(block);
  }
}

function banner(message, warning = false) {
  const node = element("div", warning ? "banner banner--warn" : "banner");
  node.setAttribute("role", "status");
  node.append(element("span", "", warning ? "⚠" : "ϟ"), element("span", "banner__text", message));
  return node;
}

function memo(kicker, text, badge, badgeClass = "") {
  const section = element("section", "memo");
  const body = element("div", "memo__body");
  const copy = element("div");
  copy.append(element("p", "memo__kicker", kicker), element("p", "memo__text", text));
  body.append(element("div", "memo__mark", "✦"), copy);
  section.append(body, element("span", `pill ${badgeClass}`.trim(), badge));
  return section;
}

function renderCard(card) {
  const article = element("article", `card${card.rank === 1 ? " card--top" : ""}`);
  const head = element("div", "card__head");
  const identity = element("div", "card__id");
  const rank = element("div", "rank num");
  rank.append(element("b", "", String(card.rank).padStart(2, "0")), element("small", "", "Match"));

  const titles = element("div", "card__titles");
  const line = element("div", "card__line");
  line.append(element("h2", "card__name", card.name));
  const ratingBadge = element(
    "span",
    "rating num",
    card.rating == null ? "Not rated" : `${card.rating.toFixed(1)} ★${card.votes ? ` (${card.votes.toLocaleString()})` : ""}`,
  );
  ratingBadge.setAttribute("aria-label", card.rating == null ? "Rating not available" : `Rating ${card.rating.toFixed(1)}`);
  line.append(ratingBadge);
  line.append(
    element(
      "span",
      "cost num",
      card.estimated_cost == null ? "Cost unavailable" : `₹${card.estimated_cost} for two`,
    ),
  );

  const meta = element("div", "card__meta");
  meta.append(element("span", "card__place", `⌖ ${card.locality || "Bangalore"}`));
  if (card.rest_types?.length) {
    meta.append(element("span", "", "•"), element("span", "", card.rest_types.join(", ")));
  }
  titles.append(line, meta);
  identity.append(rank, titles);
  head.append(identity);

  if (card.book_table || card.online_order) {
    const flags = element("div", "tags tags--flags");
    if (card.book_table) flags.append(element("span", "tag tag--mint", "Table booking"));
    if (card.online_order) flags.append(element("span", "tag tag--mint", "Online ordering"));
    head.append(flags);
  }
  article.append(head);

  const chips = element("div", "tags chips");
  const cuisines = card.cuisines?.length ? card.cuisines : [card.cuisine].filter(Boolean);
  chips.append(...cuisines.map((item) => element("span", "tag", item)));
  article.append(chips);

  const synthesis = element("div", "synthesis");
  synthesis.append(
    element("div", "synthesis__label", "✦ Why this fits your prompt"),
    element("p", "synthesis__text", card.explanation),
  );
  article.append(synthesis);

  if (card.dish_liked?.length) {
    const foot = element("div", "card__foot");
    foot.append(
      element("span", "card__foot-label", "Liked dishes:"),
      element("span", "card__foot-value", card.dish_liked.join(", ")),
    );
    article.append(foot);
  }
  return article;
}

function renderEmpty(payload) {
  results.replaceChildren();
  if (payload.message) results.append(banner(payload.message, true));
  const empty = element("div", "empty");
  empty.append(
    element("span", "empty__mark", "⌖"),
    element("p", "empty__title", "No verified matches in that sector."),
    element("p", "empty__text", "Widen the budget, lower the rating threshold, or try a nearby locality."),
  );
  if (payload.did_you_mean?.length) {
    const suggestions = element("div", "suggestions");
    for (const suggestion of payload.did_you_mean) {
      const button = element("button", "suggestion", suggestion);
      button.type = "button";
      button.addEventListener("click", () => {
        locality.value = suggestion;
        form.requestSubmit();
      });
      suggestions.append(button);
    }
    empty.append(suggestions);
  }
  results.append(empty);
}

function renderResults(payload) {
  if (!payload.recommendations?.length) {
    renderEmpty(payload);
    return;
  }

  results.replaceChildren();
  if (!payload.llm_used) {
    results.append(banner("Ranked from catalog; AI explanations unavailable"));
  }
  if (payload.message) results.append(banner(payload.message));
  if (payload.summary) {
    results.append(
      memo(
        "Neural synthesis memo",
        payload.summary,
        payload.llm_used ? "AI ranked & verified" : "Catalog ranking",
        payload.llm_used ? "pill--gold" : "",
      ),
    );
  }

  const cards = element("div", "cards");
  cards.append(...payload.recommendations.map(renderCard));
  results.append(cards);
  results.append(
    memo(
      "Data integrity pipeline active",
      "Recommendations come from a cleaned Bangalore catalog. The model only ranks restaurants that passed your filters.",
      `${payload.candidate_count} candidates screened`,
      "pill--mint",
    ),
  );
}

async function search() {
  submit.disabled = true;
  statusText.textContent = "Screening the catalog…";
  showSkeletons();

  const data = new FormData(form);
  const payload = {
    locality: data.get("locality"),
    budget: data.get("budget"),
    cuisine: data.get("cuisine") || null,
    min_rating: Number(data.get("min_rating")),
    extras: data.get("extras") || null,
  };

  try {
    const response = await fetch(`${API_BASE}/api/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Recommendation API returned ${response.status}`);
    const result = await response.json();
    renderResults(result);
    statusText.textContent = result.recommendations?.length
      ? `Screened ${result.candidate_count} candidates · ${result.llm_used ? "AI ranked" : "catalog ranked"} top ${result.recommendations.length}`
      : "No matching restaurants passed the current filters.";
  } catch (error) {
    console.error("Recommendation request failed", error);
    results.replaceChildren(
      banner("The recommendation service could not be reached. Please try again.", true),
    );
    statusText.textContent = "Search failed. Check the API connection and try again.";
  } finally {
    submit.disabled = false;
  }
}

rating.addEventListener("input", syncRating);
extras.addEventListener("input", autoGrow);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  search();
});

syncRating();
autoGrow();
loadMeta();
