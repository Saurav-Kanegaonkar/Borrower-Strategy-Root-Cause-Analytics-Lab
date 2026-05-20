import { dashboardData } from "./data.js";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const pct = (value) => `${(Number(value) * 100).toFixed(1)}%`;
const moneyShort = (value) => {
  const amount = Number(value);
  if (Math.abs(amount) >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
  if (Math.abs(amount) >= 1000) return `$${(amount / 1000).toFixed(0)}K`;
  return currency.format(amount);
};

function renderMetrics() {
  const strip = document.querySelector("#metricStrip");
  strip.innerHTML = dashboardData.metrics
    .map(
      (metric) => `
        <article>
          <span>${metric.label}</span>
          <strong>${metric.value}</strong>
          <em>${metric.note}</em>
        </article>
      `
    )
    .join("");

  document.querySelector("#topRecommendation").textContent = dashboardData.portfolio.top_recommendation;
  document.querySelector("#topSegment").textContent = dashboardData.portfolio.top_segment;
}

function renderPriorityRows() {
  const rows = dashboardData.rootCauseQueue
    .slice(0, 6)
    .map(
      (row) => `
        <tr>
          <td>
            <strong>${row.segment}</strong>
            <span>${row.product}</span>
          </td>
          <td>${row.primary_root_cause}</td>
          <td>${pct(row.avg_delinquency_rate)}</td>
          <td>${moneyShort(row.modeled_net_value)}</td>
        </tr>
      `
    )
    .join("");
  document.querySelector("#priorityRows").innerHTML = rows;
}

function renderThemes() {
  const max = Math.max(...dashboardData.themeRollup.map((theme) => theme.complaints));
  document.querySelector("#themeBars").innerHTML = dashboardData.themeRollup
    .slice(0, 6)
    .map(
      (theme) => `
        <article>
          <div>
            <strong>${theme.issue}</strong>
            <span>${theme.borrower_signal}</span>
          </div>
          <div class="bar-track">
            <i style="width:${Math.max(8, (theme.complaints / max) * 100)}%"></i>
          </div>
          <em>${theme.complaints.toLocaleString()} complaints</em>
        </article>
      `
    )
    .join("");
}

function renderActions() {
  document.querySelector("#actionCards").innerHTML = dashboardData.actionPlan
    .slice(0, 3)
    .map(
      (action) => `
        <article>
          <span>Rank ${action.rank}</span>
          <h3>${action.segment}</h3>
          <strong>${action.recommendation}</strong>
          <p>${action.decision_reason}</p>
          <footer>
            <b>${action.owner}</b>
            <em>${moneyShort(action.modeled_net_value)}</em>
          </footer>
        </article>
      `
    )
    .join("");
}

function renderRootCause() {
  const top = dashboardData.rootCauseQueue[0];
  const signals = [
    ["Delinquency rate", top.avg_delinquency_rate, "higher means more repayment risk"],
    ["Contact demand", top.avg_contact_rate, "higher means more servicing friction"],
    ["Autopay gap", top.autopay_gap, "higher means more payment fragility"],
    ["Low first resolution", 1 - top.avg_first_resolution_rate, "higher means repeated support demand"],
    ["Model confidence", top.confidence, "higher means stronger operating trust"],
  ];

  document.querySelector("#diagnosticStack").innerHTML = signals
    .map(
      ([label, value, note]) => `
        <article>
          <div>
            <strong>${label}</strong>
            <span>${note}</span>
          </div>
          <meter min="0" max="1" value="${value}"></meter>
          <em>${pct(value)}</em>
        </article>
      `
    )
    .join("");

  document.querySelector("#briefCard").innerHTML = `
    <p class="brief-label">Primary root cause</p>
    <h3>${top.primary_root_cause}</h3>
    <p>${top.segment} shows ${pct(top.avg_delinquency_rate)} modeled delinquency, ${pct(top.avg_contact_rate)} contact demand, and a ${pct(top.autopay_gap)} autopay gap. The public theme signal is ${top.public_theme_signal.toLowerCase()}.</p>
    <dl>
      <div><dt>Recommended action</dt><dd>${top.recommended_action}</dd></div>
      <div><dt>Owner</dt><dd>${top.action_owner}</dd></div>
      <div><dt>Expected risk pool</dt><dd>${moneyShort(top.expected_loss_risk)}</dd></div>
    </dl>
  `;
}

function renderForecast() {
  const topSegments = dashboardData.actionPlan.slice(0, 3).map((item) => item.segment_id);
  const grouped = topSegments.map((segmentId) => ({
    segmentId,
    rows: dashboardData.scenarioForecast.filter((row) => row.segment_id === segmentId),
  }));

  document.querySelector("#scenarioGrid").innerHTML = grouped
    .map(({ rows }) => {
      const segment = rows[0].segment;
      return `
        <article>
          <h3>${segment}</h3>
          ${rows
            .map(
              (row) => `
                <div class="scenario-row">
                  <span>${row.scenario}</span>
                  <b>${pct(row.forecast_delinquency_rate)}</b>
                  <em>${moneyShort(Number(row.annualized_value) - Number(row.operating_cost))}</em>
                </div>
              `
            )
            .join("")}
        </article>
      `;
    })
    .join("");
}

function renderQuality() {
  document.querySelector("#qualityChecks").innerHTML = dashboardData.qualityChecks
    .map(
      (check) => `
        <article class="${check.status.toLowerCase()}">
          <div>
            <strong>${check.check_name}</strong>
            <span>${check.dataset}</span>
          </div>
          <b>${check.status}</b>
          <em>${pct(check.confidence)}</em>
        </article>
      `
    )
    .join("");
}

function wireTabs() {
  document.querySelectorAll(".surface-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".surface-tabs button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".surface").forEach((surface) => surface.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`#${button.dataset.surface}`).classList.add("active");
    });
  });
}

renderMetrics();
renderPriorityRows();
renderThemes();
renderActions();
renderRootCause();
renderForecast();
renderQuality();
wireTabs();
