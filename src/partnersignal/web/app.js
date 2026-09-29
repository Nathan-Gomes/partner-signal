const state = { partners: [], filter: "All" };

const stageOrder = ["Contacted", "Discovery", "Qualified", "Technical review", "Proposal", "Nurture"];
const serviceOrder = ["Cybersecurity assessment", "Cloud migration discovery", "Networking assessment", "AI readiness workshop", "Technical training plan"];

function iconify() { window.lucide?.createIcons({ attrs: { "stroke-width": 1.7 } }); }
function initials(value) { return value.split(" ").map(part => part[0]).slice(0, 2).join(""); }
function escapeHtml(value) { const el = document.createElement("div"); el.textContent = value; return el.innerHTML; }

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function stageClass(stage) { return stage.replaceAll(" ", "-"); }

function renderOverview(overview) {
  document.querySelector("#metric-partners").textContent = overview.partners;
  document.querySelector("#metric-qualified").textContent = overview.qualified;
  document.querySelector("#metric-followups").textContent = overview.follow_ups_due;
  document.querySelector("#metric-score").textContent = `${overview.average_score}%`;
  document.querySelector("#partner-count").textContent = overview.partners;
  document.querySelector("#follow-up-nav").textContent = overview.follow_ups_due;
  const max = Math.max(...Object.values(overview.services));
  document.querySelector("#service-bars").innerHTML = serviceOrder.filter(service => overview.services[service]).map(service => `
    <div class="service-bar-row"><strong>${service}</strong><div class="bar-track"><span class="bar-fill" style="width:${(overview.services[service] / max) * 100}%"></span></div><span>${overview.services[service]}</span></div>`).join("");
}

function visiblePartners() {
  if (state.filter === "Due") return state.partners.filter(partner => !partner.follow_up_complete);
  if (state.filter === "Qualified") return state.partners.filter(partner => ["Qualified", "Technical review", "Proposal"].includes(partner.stage));
  return state.partners;
}

function renderFollowUps() {
  const due = state.partners.filter(partner => !partner.follow_up_complete).slice(0, 4);
  const container = document.querySelector("#follow-up-list");
  if (!due.length) { container.innerHTML = document.querySelector("#empty-template").innerHTML; iconify(); return; }
  container.innerHTML = due.map(partner => `
    <div class="follow-up-item"><span class="company-initial">${initials(partner.company)}</span><div><h3>${partner.company}</h3><p>${partner.recommended_service} · ${partner.specialist}</p></div><div><span class="due-label">${partner.next_follow_up}</span><button class="row-action" data-open="${partner.id}" type="button">Review</button></div></div>`).join("");
}

function renderTable() {
  document.querySelector("#partner-table").innerHTML = visiblePartners().map(partner => `
    <tr><td><div class="partner-name"><span class="company-initial">${initials(partner.company)}</span><div><b>${partner.company}</b><span>${partner.contact_name} · ${partner.region}</span></div></div></td>
    <td><div class="score"><b>${partner.opportunity_score}</b><div class="score-track"><span style="width:${partner.opportunity_score}%"></span></div></div></td>
    <td class="service-cell">${partner.recommended_service}</td><td><span class="stage ${stageClass(partner.stage)}">${partner.stage}</span></td>
    <td>${partner.follow_up_complete ? "Complete" : partner.next_follow_up}</td><td><button class="table-detail" data-open="${partner.id}" type="button">Open <i data-lucide="arrow-up-right"></i></button></td></tr>`).join("");
  iconify();
}

function renderPipeline() {
  const relevantStages = stageOrder.filter(stage => state.partners.some(partner => partner.stage === stage));
  document.querySelector("#pipeline-board").innerHTML = relevantStages.map(stage => {
    const partners = state.partners.filter(partner => partner.stage === stage);
    return `<div class="pipeline-column"><h3>${stage}<span>${partners.length}</span></h3>${partners.map(partner => `<button class="pipeline-card" data-open="${partner.id}" type="button"><b>${partner.company}</b><p>${partner.recommended_service}</p><span class="mini-score">Fit score ${partner.opportunity_score}</span></button>`).join("")}</div>`;
  }).join("");
}

async function openPartner(id) {
  const partner = state.partners.find(item => item.id === id) || await getJson(`/api/partners/${id}`);
  const draft = await getJson(`/api/partners/${id}/outreach`);
  const dialog = document.querySelector("#partner-dialog");
  document.querySelector("#dialog-content").innerHTML = `
    <div class="partner-detail-head"><div><p class="eyebrow">${partner.vertical} · ${partner.region}</p><h2>${partner.company}</h2><p>${partner.contact_name} · ${partner.stage}</p></div><div class="detail-score"><b>${partner.opportunity_score}</b><span>opportunity fit</span></div></div>
    <div class="detail-grid"><div class="detail-group"><h3>Customer challenge</h3><p>${partner.challenge}</p></div><div class="detail-group"><h3>Recommended handoff</h3><p><b>${partner.recommended_service}</b><br>${partner.specialist}</p></div><div class="detail-group"><h3>Signals considered</h3><div class="signal-list">${partner.reasoning.map(reason => `<span>${reason}</span>`).join("")}</div></div><div class="detail-group"><h3>Discovery notes</h3><p>${partner.notes}</p></div></div>
    <div class="outreach-box"><h3>Personalized discovery draft</h3><p class="eyebrow">Suggested subject: ${draft.subject}</p><pre>${draft.body}</pre></div>
    <div class="dialog-actions"><button id="copy-draft" class="secondary-button" type="button"><i data-lucide="copy"></i>Copy draft</button>${partner.follow_up_complete ? `<span class="data-chip"><span></span> Follow-up complete</span>` : `<button id="complete-follow-up" class="primary-button" type="button"><i data-lucide="check"></i>Mark follow-up complete</button>`}</div>`;
  dialog.showModal(); iconify();
  document.querySelector("#copy-draft")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    document.querySelector("#copy-draft").innerHTML = '<i data-lucide="check"></i>Copied'; iconify();
  });
  document.querySelector("#complete-follow-up")?.addEventListener("click", async () => {
    const updated = await getJson(`/api/partners/${id}/complete-follow-up`, { method: "POST" });
    state.partners = state.partners.map(item => item.id === id ? updated : item);
    const overview = await getJson("/api/overview");
    renderOverview(overview); renderFollowUps(); renderTable(); renderPipeline(); dialog.close();
  });
}

function attachEvents() {
  document.addEventListener("click", event => {
    const open = event.target.closest("[data-open]");
    if (open) openPartner(open.dataset.open);
  });
  document.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button));
    renderTable();
  }));
  document.querySelector("#partner-dialog .dialog-close").addEventListener("click", () => document.querySelector("#partner-dialog").close());
  document.querySelector("#method-dialog .dialog-close").addEventListener("click", () => document.querySelector("#method-dialog").close());
  document.querySelector("#open-method").addEventListener("click", () => document.querySelector("#method-dialog").showModal());
}

async function init() {
  try {
    const [overview, partners] = await Promise.all([getJson("/api/overview"), getJson("/api/partners")]);
    state.partners = partners;
    renderOverview(overview); renderFollowUps(); renderTable(); renderPipeline(); attachEvents(); iconify();
  } catch (error) {
    document.querySelector(".main-content").insertAdjacentHTML("afterbegin", `<div class="insight-bar"><div class="insight-icon"><i data-lucide="triangle-alert"></i></div><p><b>Unable to load demo data.</b> Refresh the page to try again.</p></div>`); iconify();
  }
}

init();
