import { buildRegionExportViewModel } from "./region-export-view-model.js";
import { getMockRegionExport } from "../mock/region-exports.js";
import { formatDateTime } from "./view-model-utils.js";

const overviewRoot = document.querySelector("#overviewRoot");
const capabilityRoot = document.querySelector("#capabilityRoot");
const assessmentRoot = document.querySelector("#assessmentRoot");
const gapRoot = document.querySelector("#gapRoot");
const recommendationRoot = document.querySelector("#recommendationRoot");
const evidenceRoot = document.querySelector("#evidenceRoot");
const regionName = document.querySelector("#regionName");
const generatedAt = document.querySelector("#generatedAt");
const schemaVersion = document.querySelector("#schemaVersion");
const demoNotice = document.querySelector("#demoNotice");
const evidenceDialog = document.querySelector("#evidenceDialog");
const evidenceBody = document.querySelector("#evidenceBody");
const closeEvidence = document.querySelector("#closeEvidence");
const regionOptions = document.querySelector("#regionOptions");
const regionButtons = [...regionOptions.querySelectorAll("[data-region-key]")];

function element(tagName, options = {}) {
  const node = document.createElement(tagName);

  if (options.className) node.className = options.className;
  if (options.text !== undefined) node.textContent = options.text;

  for (const [name, value] of Object.entries(options.attributes ?? {})) {
    node.setAttribute(name, value);
  }

  for (const child of options.children ?? []) {
    node.append(child);
  }

  return node;
}

function statusBadge(label, tone, className = "status-badge") {
  return element("span", {
    className: `${className} tone-${tone}`,
    text: label,
  });
}

function reasonList(reasons, emptyMessage) {
  const items = reasons.length ? reasons : [emptyMessage];
  return element("ul", {
    className: "reason-list",
    children: items.map((reason) => element("li", { text: reason })),
  });
}

function emptyState(message) {
  return element("div", {
    className: "empty-state",
    children: [
      element("span", { className: "empty-state-mark", text: "—" }),
      element("p", { text: message }),
    ],
  });
}

function definitionRow(term, value) {
  return [element("dt", { text: term }), element("dd", { text: value ?? "情報なし" })];
}

function evidenceDetails(evidence) {
  const details = element("dl", { className: "evidence-data" });
  details.append(
    ...definitionRow("提供元", evidence.publisher),
    ...definitionRow(
      "公開日時",
      evidence.publishedAt ? formatDateTime(evidence.publishedAt) : "未確認",
    ),
    ...definitionRow(
      "取得日時",
      evidence.fetchedAt ? formatDateTime(evidence.fetchedAt) : null,
    ),
    ...definitionRow("形式", evidence.sourceFormat),
    ...definitionRow("取得方法", evidence.retrievalMethod),
    ...definitionRow("ライセンス", evidence.license),
    ...definitionRow("注記", evidence.notes),
  );

  const urlTerm = element("dt", { text: "参照URL" });
  const urlValue = element("dd");
  if (evidence.sourceUrl) {
    urlValue.append(
      element("a", {
        text: evidence.sourceUrl,
        attributes: { href: evidence.sourceUrl, target: "_blank", rel: "noreferrer" },
      }),
    );
  } else {
    urlValue.textContent = "情報なし";
  }
  details.append(urlTerm, urlValue);
  return details;
}

function evidenceDialogCard(evidence) {
  return element("article", {
    className: "evidence-item",
    children: [
      element("h3", { text: evidence.sourceName }),
      element("p", { text: `requirement_code: ${evidence.requirementCode}` }),
      evidenceDetails(evidence),
    ],
  });
}

function openEvidence(evidence) {
  evidenceBody.replaceChildren();

  if (!evidence.length) {
    evidenceBody.append(
      element("p", {
        text: "関連するEvidenceはRegionExportに含まれていません。",
      }),
    );
  } else {
    evidenceBody.append(...evidence.map(evidenceDialogCard));
  }

  evidenceDialog.showModal();
}

function dependencyCard(dependency) {
  const reason = dependency.reasons.length
    ? dependency.reasons.join(" ")
    : "依存データの評価理由は提供されていません。";

  return element("article", {
    className: "dependency-item",
    children: [
      element("div", {
        className: "dependency-head",
        children: [
          element("span", { className: "dependency-code", text: dependency.requirementCode }),
          statusBadge(dependency.statusLabel, dependency.tone, "dependency-status"),
        ],
      }),
      element("div", {
        className: "dependency-criticality",
        text: `Capability内の重要度：${dependency.criticality}`,
      }),
      element("p", { className: "dependency-reason", text: reason }),
    ],
  });
}

function capabilityCard(viewModel) {
  const evidenceButton = element("button", {
    className: "primary-button",
    text: `関連Evidence（${viewModel.evidence.length}件）`,
    attributes: { type: "button" },
  });
  evidenceButton.addEventListener("click", () => openEvidence(viewModel.evidence));

  const dependencyContent = viewModel.dependencies.length
    ? viewModel.dependencies.map(dependencyCard)
    : [element("p", { className: "dependency-reason", text: "依存データ情報はありません。" })];

  const scopeNote = viewModel.scopeNote
    ? element("p", { className: "semantic-note", text: viewModel.scopeNote })
    : null;

  return element("article", {
    className: `capability-card tone-${viewModel.tone}`,
    attributes: { "data-status": viewModel.statusCode },
    children: [
      element("div", {
        className: "card-top",
        children: [
          element("div", {
            children: [
              element("div", {
                className: "card-title-row",
                children: [
                  element("h3", { text: viewModel.capabilityName }),
                  element("span", { className: "code-pill", text: viewModel.capabilityCode }),
                ],
              }),
              element("div", {
                className: "status-line",
                children: [statusBadge(viewModel.statusLabel, viewModel.tone)],
              }),
            ],
          }),
          element("p", { className: "status-copy", text: viewModel.statusDescription }),
        ],
      }),
      scopeNote,
      element("div", {
        className: "card-grid",
        children: [
          element("section", {
            className: "card-section",
            children: [
              element("div", { className: "section-label", text: "評価理由" }),
              reasonList(viewModel.reasons, "Capabilityの評価理由は提供されていません。"),
            ],
          }),
          element("section", {
            className: "card-section",
            children: [
              element("div", { className: "section-label", text: "依存データ" }),
              element("div", { className: "dependency-list", children: dependencyContent }),
            ],
          }),
        ],
      }),
      element("div", {
        className: "card-bottom",
        children: [
          element("p", {
            className: "assessed-at",
            text: `評価日時：${viewModel.assessedAt} / Engine ${viewModel.engineVersion}`,
          }),
          element("div", { className: "card-actions", children: [evidenceButton] }),
        ],
      }),
    ].filter(Boolean),
  });
}

function metricCard(metric) {
  return element("article", {
    className: `metric-card metric-${metric.tone}`,
    attributes: {
      "data-metric": metric.key,
      "data-score": metric.score === null ? "null" : String(metric.score),
    },
    children: [
      element("div", {
        className: "metric-head",
        children: [
          element("h4", { text: metric.label }),
          element("span", {
            className: `metric-score ${metric.isUnassessed ? "metric-score--unassessed" : ""}`,
            text: metric.scoreLabel,
          }),
        ],
      }),
      element("p", { text: metric.reason }),
    ],
  });
}

function metricGroup(title, subtitle, metrics) {
  return element("section", {
    className: "metric-group",
    children: [
      element("div", {
        className: "metric-group-heading",
        children: [element("h4", { text: title }), element("p", { text: subtitle })],
      }),
      element("div", { className: "metric-grid", children: metrics.map(metricCard) }),
    ],
  });
}

function assessmentCard(assessment) {
  return element("article", {
    className: "assessment-card",
    children: [
      element("header", {
        className: "assessment-header",
        children: [
          element("div", {
            children: [
              element("p", { className: "eyebrow", text: "Data requirement" }),
              element("h3", { text: assessment.requirementCode }),
            ],
          }),
          statusBadge(assessment.discoveryLabel, assessment.tone),
        ],
      }),
      element("div", {
        className: "dataset-summary",
        children: [
          element("div", {
            children: [
              element("strong", { text: assessment.recordCountLabel }),
              element("p", { text: assessment.recordCountNote }),
              element("p", { text: assessment.discoveryDescription }),
            ],
          }),
          element("p", { className: "scope-note", text: assessment.scopeNote }),
        ],
      }),
      element("section", {
        className: "findings",
        children: [
          element("div", { className: "section-label", text: "Findings" }),
          reasonList(assessment.findings, "追加の所見はありません。"),
        ],
      }),
      metricGroup("Data Quality", "データそのものの品質評価", assessment.dataQuality),
      metricGroup(
        "Application Readiness",
        "アプリケーションで利用するための適性評価",
        assessment.applicationReadiness,
      ),
      element("footer", {
        className: "assessment-footer",
        text: `評価日時：${assessment.assessedAt} / Assessment ${assessment.assessmentVersion}`,
      }),
    ],
  });
}

function gapCard(gap) {
  return element("article", {
    className: `info-card tone-${gap.tone}`,
    attributes: { "data-gap-kind": gap.kindCode },
    children: [
      element("div", {
        className: "info-card-head",
        children: [
          statusBadge(gap.kindLabel, gap.tone),
          element("span", {
            className: `severity-pill tone-${gap.severityTone}`,
            text: `${gap.severityDisplayLabel} ${gap.severityLabel}`,
          }),
        ],
      }),
      element("h3", { text: gap.requirementCode }),
      element("p", { className: "info-card-copy", text: gap.reason }),
      element("p", { className: "semantic-note semantic-note--compact", text: gap.kindDescription }),
      element("div", {
        className: "info-card-meta",
        text: `${gap.capabilityCode} / Capability ${gap.capabilityStatus ?? "情報なし"}`,
      }),
    ],
  });
}

function recommendationCard(recommendation) {
  return element("article", {
    className: `info-card tone-${recommendation.tone}`,
    attributes: { "data-recommendation-type": recommendation.typeCode },
    children: [
      element("div", {
        className: "info-card-head",
        children: [
          statusBadge(recommendation.typeLabel, recommendation.tone),
          element("span", {
            className: `severity-pill tone-${recommendation.priorityTone}`,
            text: `${recommendation.priorityDisplayLabel} ${recommendation.priorityLabel}`,
          }),
        ],
      }),
      element("h3", { text: recommendation.title }),
      element("p", { className: "info-card-copy", text: recommendation.rationale }),
      element("section", {
        className: "action-block",
        children: [
          element("div", { className: "section-label", text: "Actions" }),
          reasonList(recommendation.actions, "具体的なactionは提供されていません。"),
        ],
      }),
      element("div", {
        className: "info-card-meta",
        text: `${recommendation.capabilityCode} / ${recommendation.requirementCode}`,
      }),
    ],
  });
}

function evidenceSummaryCard(evidence) {
  const button = element("button", {
    className: "text-button",
    text: "詳細を見る",
    attributes: { type: "button" },
  });
  button.addEventListener("click", () => openEvidence([evidence]));

  return element("article", {
    className: "evidence-summary-card",
    children: [
      element("div", {
        className: "evidence-summary-head",
        children: [
          element("span", { className: "code-pill", text: evidence.requirementCode }),
          element("span", {
            className: "published-state",
            text: evidence.publishedAt ? `公開 ${formatDateTime(evidence.publishedAt)}` : "公開日 未確認",
          }),
        ],
      }),
      element("h3", { text: evidence.sourceName }),
      element("p", { text: evidence.notes ?? "Evidenceの注記は提供されていません。" }),
      button,
    ],
  });
}

function renderOverview(viewModel) {
  const items = [
    ["地域コード", viewModel.regionCode],
    ["Datasets", viewModel.counts.datasets],
    ["Capabilities", viewModel.counts.capabilities],
    ["Gaps", viewModel.counts.gaps],
    ["Recommendations", viewModel.counts.recommendations],
  ];

  overviewRoot.replaceChildren(
    ...items.map(([label, value], index) =>
      element("article", {
        className: `overview-item ${index === 0 ? "overview-item--wide" : ""}`,
        children: [element("span", { text: label }), element("strong", { text: value })],
      }),
    ),
  );
}

function renderCollection(root, items, renderer, emptyMessage) {
  root.replaceChildren(...(items.length ? items.map(renderer) : [emptyState(emptyMessage)]));
}

function updateSelectedRegion(regionKey) {
  for (const button of regionButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.regionKey === regionKey));
  }
}

function renderPage(viewModel) {
  regionName.textContent = viewModel.regionName;
  generatedAt.textContent = `仮データ生成：${viewModel.generatedAt}`;
  schemaVersion.textContent = `Contract ${viewModel.schemaVersion}`;
  demoNotice.hidden = !viewModel.isSynthetic;

  renderOverview(viewModel);
  renderCollection(
    capabilityRoot,
    viewModel.capabilities,
    capabilityCard,
    "表示できるCapabilityはありません。",
  );
  renderCollection(
    assessmentRoot,
    viewModel.assessments,
    assessmentCard,
    "Dataset Assessmentはありません。",
  );
  renderCollection(gapRoot, viewModel.gaps, gapCard, "現在のRegionExportにGapはありません。");
  renderCollection(
    recommendationRoot,
    viewModel.recommendations,
    recommendationCard,
    "現在のRegionExportにRecommendationはありません。",
  );
  renderCollection(
    evidenceRoot,
    viewModel.evidence,
    evidenceSummaryCard,
    "現在のRegionExportにEvidenceはありません。",
  );
}

function selectMockRegion(regionKey) {
  updateSelectedRegion(regionKey);
  if (evidenceDialog.open) evidenceDialog.close();
  renderPage(buildRegionExportViewModel(getMockRegionExport(regionKey)));
}

closeEvidence.addEventListener("click", () => evidenceDialog.close());
evidenceDialog.addEventListener("click", (event) => {
  if (event.target === evidenceDialog) evidenceDialog.close();
});

for (const button of regionButtons) {
  button.addEventListener("click", () => selectMockRegion(button.dataset.regionKey));
}

selectMockRegion("edogawa");
