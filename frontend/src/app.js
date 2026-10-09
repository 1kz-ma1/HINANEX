import { buildRegionExportViewModel } from "./region-export-view-model.js";
import { createRegionExportController } from "./region-export-loader.js";
import {
  assertRegionMatches,
  buildGisRegionUrl,
  getPayloadRegionCode,
} from "./region-export-source.js";
import { buildAnalysisSummary, isSelectedRegion } from "./presentation-view-model.js";
import { formatDateTime } from "./view-model-utils.js";

const summaryRoot = document.querySelector("#summaryRoot");
const overviewRoot = document.querySelector("#overviewRoot");
const capabilityRoot = document.querySelector("#capabilityRoot");
const floodScenarioRoot = document.querySelector("#floodScenarioRoot");
let scenarioPageIndex = 0;
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
const regionSelect = document.querySelector("#regionSelect");
const reloadRegionExport = document.querySelector("#reloadRegionExport");
const regionExportFile = document.querySelector("#regionExportFile");
const loadDemoData = document.querySelector("#loadDemoData");
const sourceStatus = document.querySelector("#sourceStatus");
const regionButtons = [...document.querySelectorAll("[data-region-code]")];
const contentRoots = [
  summaryRoot,
  overviewRoot,
  capabilityRoot,
  floodScenarioRoot,
  assessmentRoot,
  gapRoot,
  recommendationRoot,
  evidenceRoot,
];

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
    ...definitionRow("対象データ", evidence.requirementLabel),
    ...definitionRow("出典", evidence.sourceName),
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

function evidenceTechnicalDetails(evidence) {
  return element("details", {
    className: "technical-details",
    children: [
      element("summary", { text: "詳細情報" }),
      element("dl", {
        className: "evidence-data evidence-data--technical",
        children: [
          ...definitionRow("requirement_code", evidence.requirementCode),
          ...definitionRow("取得方法", evidence.retrievalMethod),
        ],
      }),
    ],
  });
}

function evidenceDialogCard(evidence) {
  return element("article", {
    className: "evidence-item",
    children: [
      element("h3", { text: evidence.requirementLabel }),
      evidenceDetails(evidence),
      evidenceTechnicalDetails(evidence),
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

function metricGroup(title, technicalLabel, subtitle, metrics) {
  return element("details", {
    className: "metric-group",
    children: [
      element("summary", {
        className: "metric-group-heading",
        children: [
          element("div", {
            children: [
              element("h4", { text: title }),
              element("small", { text: technicalLabel }),
              element("p", { text: subtitle }),
            ],
          }),
          element("div", {
            className: "metric-disclosure",
            children: [
              element("strong", { text: `${metrics.length}項目` }),
              element("span", { className: "metric-disclosure-closed", text: "詳細を見る" }),
              element("span", { className: "metric-disclosure-open", text: "閉じる" }),
            ],
          }),
        ],
      }),
      element("div", {
        className: "metric-group-content",
        children: [element("div", { className: "metric-grid", children: metrics.map(metricCard) })],
      }),
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
              element("p", { className: "eyebrow", text: "対象データ" }),
              element("div", {
                className: "card-title-row",
                children: [
                  element("h3", { text: assessment.requirementLabel }),
                  element("span", { className: "code-pill", text: assessment.requirementCode }),
                ],
              }),
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
          element("div", { className: "section-label", text: "所見 / Findings" }),
          reasonList(assessment.findings, "追加の所見はありません。"),
        ],
      }),
      element("p", {
        className: "score-explanation",
        text: "HINANEXでは0点と未評価を区別しています。0 / 4は評価結果として0、未評価はscore=nullで、情報不足などにより評価できていない状態です。各項目ではRegionExportの評価理由を優先して表示します。",
      }),
      metricGroup(
        "データ品質",
        "Data Quality",
        "データそのものの品質評価",
        assessment.dataQuality,
      ),
      metricGroup(
        "アプリ利用適性",
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
  return element("article", {
    className: "evidence-summary-card",
    children: [
      element("div", {
        className: "evidence-summary-head",
        children: [
          element("span", { className: "evidence-target", text: evidence.requirementLabel }),
          element("span", {
            className: "published-state",
            text: evidence.publishedAt ? `公開 ${formatDateTime(evidence.publishedAt)}` : "公開日 未確認",
          }),
        ],
      }),
      evidenceDetails(evidence),
      evidenceTechnicalDetails(evidence),
    ],
  });
}

function summaryMetric(label, value, className = "") {
  return element("article", {
    className: `summary-metric ${className}`.trim(),
    children: [element("span", { text: label }), element("strong", { text: value })],
  });
}

function renderAnalysisSummary(viewModel) {
  const summary = buildAnalysisSummary(viewModel);
  const capabilityStatus = element("div", {
    className: "summary-capability-status",
    children: [
      element("strong", { text: summary.capabilityName }),
      statusBadge(summary.capabilityStatusLabel, summary.capabilityTone),
    ],
  });

  const summaryActions = [];
  if (!viewModel.isSynthetic) {
    summaryActions.push(
      element("a", {
        className: "gis-cta",
        text: "地図で避難所を確認",
        attributes: { href: buildGisRegionUrl(viewModel.regionCode) },
      }),
    );
  }

  summaryRoot.replaceChildren(
    element("article", {
      className: `summary-card tone-${summary.capabilityTone}`,
      attributes: {
        "data-capability-status": summary.capabilityStatusCode ?? "none",
      },
      children: [
        element("header", {
          className: "summary-header",
          children: [
            element("div", {
              children: [
                element("span", { className: "summary-label", text: "対象地域" }),
                element("h3", { text: summary.regionName }),
              ],
            }),
            element("div", { className: "summary-actions", children: summaryActions }),
          ],
        }),
        element("div", {
          className: "summary-grid",
          children: [
            element("article", {
              className: "summary-metric summary-metric--capability",
              children: [element("span", { text: "できること" }), capabilityStatus],
            }),
            summaryMetric("現在取得しているデータ", summary.recordCountLabel),
            summaryMetric("課題", `${summary.gapCount}件`),
            summaryMetric("改善・調査提案", `${summary.recommendationCount}件`),
          ],
        }),
        summary.scopeNote
          ? element("p", { className: "summary-scope-note", text: summary.scopeNote })
          : null,
        element("footer", {
          className: "summary-footer",
          text: `データ生成日時：${summary.generatedAt}`,
        }),
      ].filter(Boolean),
    }),
  );
}

const SCENARIO_PAGE_SIZE = 20;

function renderFloodScenario(scenario, context = {}) {
  floodScenarioRoot.replaceChildren();

  if (scenario.uiState !== "ready") {
    const stateContent = {
      loading: {
        title: "Scenario結果を読み込み中",
        message: scenario.message ?? "選択した地域の洪水Scenario Resultを取得しています。",
        mark: "…",
      },
      empty: {
        title: "Scenario結果なし",
        message: scenario.message,
        mark: "—",
      },
      error: {
        title: "Scenario結果の取得に失敗",
        message: scenario.message,
        mark: "!",
      },
      unsupported: {
        title: "未対応のScenario Contract",
        message: scenario.message,
        mark: "!",
      },
    }[scenario.uiState];

    floodScenarioRoot.append(
      element("div", {
        className: `scenario-state scenario-state--${scenario.uiState}`,
        attributes: { role: scenario.uiState === "error" ? "alert" : "status" },
        children: [
          element("span", {
            className: "scenario-state-mark",
            text: stateContent?.mark ?? "!",
            attributes: { "aria-hidden": "true" },
          }),
          element("strong", { text: stateContent?.title ?? "Scenarioを表示できません" }),
          element("p", { text: stateContent?.message ?? "表示状態を確認してください。" }),
          scenario.uiState === "empty"
            ? element("small", { text: "候補が0件という意味ではありません。" })
            : null,
        ].filter(Boolean),
      }),
    );
    return;
  }

  const pages = Math.max(1, Math.ceil(scenario.rows.length / SCENARIO_PAGE_SIZE));
  scenarioPageIndex = Math.min(scenarioPageIndex, pages - 1);
  const start = scenarioPageIndex * SCENARIO_PAGE_SIZE;
  const selected = scenario.rows.slice(start, start + SCENARIO_PAGE_SIZE);

  const summary = element("section", {
    className: `scenario-summary tone-${scenario.statusTone}`,
    attributes: { "aria-labelledby": "scenarioSummaryTitle" },
    children: [
      element("header", {
        className: "scenario-summary-header",
        children: [
          element("div", {
            children: [
              element("span", { className: "summary-label", text: "洪水時の避難候補探索" }),
              element("h3", {
                text: scenario.name,
                attributes: { id: "scenarioSummaryTitle" },
              }),
            ],
          }),
          statusBadge(scenario.statusLabel, scenario.statusTone),
        ],
      }),
      element("p", { className: "scenario-assessment-reason", text: scenario.assessmentReason }),
      element("div", {
        className: "scenario-metrics",
        children: [
          summaryMetric("対象施設（D出力）", `${scenario.recordCount}件`),
          summaryMetric("同じ公式Sourceで照合（D出力）", `${scenario.directlyJoinedCount}件`),
          summaryMetric("公式raw値あり（D出力）", `${scenario.rawValueCount}件`),
          summaryMetric("公式情報の取得状態", scenario.discoveryStatusLabel),
        ],
      }),
      element("p", {
        className: "scenario-technical-line",
        text: `D原値: status=${scenario.statusCode} / discovery_status=${scenario.discoveryStatusCode} / 評価日時=${scenario.evaluatedAt}`,
      }),
    ],
  });

  const note = element("div", {
    className: "scenario-alert",
    attributes: { role: "note" },
    children: [
      element("strong", { text: "洪水時の安全・開設を保証する情報ではありません" }),
      element("p", { text: scenario.caveat }),
    ],
  });

  const cards = selected.map((row) => {
    const source = row.sourceUrl
      ? element("a", {
          text: "公式Sourceを確認",
          attributes: { href: row.sourceUrl, target: "_blank", rel: "noopener noreferrer" },
        })
      : element("span", { text: "安全に開けるHTTPSの出典URLなし" });

    const evidence = element("dl", { className: "scenario-facts" });
    evidence.append(
      ...definitionRow("公式項目", row.hazardScopeRaw),
      ...definitionRow("Source固有の意味", row.sourceSemantics),
      ...definitionRow("公式記録の原文", row.rawValue ?? "D出力では値なし"),
      ...definitionRow("利用階の原文", row.floorRaw ?? "D出力では値なし"),
      ...definitionRow("施設行の照合", row.joinStatusLabel),
      ...definitionRow("元データの記録", row.sourceTrace ?? "施設単位の記録なし"),
      ...definitionRow(
        "位置情報",
        row.hasCoordinates ? "D出力に座標あり" : "D出力では座標なし（推測補完なし）",
      ),
    );

    return element("article", {
      className: `scenario-facility tone-${row.statusTone}`,
      attributes: { "data-facility-status": row.statusCode },
      children: [
        element("div", {
          className: "scenario-facility-header",
          children: [
            element("div", {
              children: [
                element("span", { className: "scenario-facility-mark", text: row.statusMark }),
                element("h3", { text: row.name }),
              ],
            }),
            statusBadge(row.statusLabel, row.statusTone),
          ],
        }),
        element("p", { className: "scenario-status-help", text: row.statusHelp }),
        element("section", {
          className: "scenario-reason-block",
          children: [
            element("h4", { text: "判定理由" }),
            element("p", { text: row.reason }),
          ],
        }),
        element("details", {
          className: "scenario-evidence",
          children: [
            element("summary", { text: "根拠を見る" }),
            evidence,
            element("div", { className: "scenario-source-link", children: [source] }),
            element("p", {
              className: "scenario-technical-line",
              text: `技術情報: facility_id=${row.facilityId} / status=${row.statusCode} / join_status=${row.joinStatusCode}`,
            }),
          ],
        }),
      ],
    });
  });

  const scenarioNotes = [
    ["Dの判定理由", scenario.reasons],
    ["データ上の制約", scenario.gaps],
    ["次に必要な確認", scenario.recommendations],
  ]
    .filter(([, items]) => items.length)
    .map(([title, items]) =>
      element("section", {
        className: "scenario-note-block",
        children: [element("h3", { text: title }), reasonList(items, "記録なし")],
      }),
    );

  const previous = element("button", {
    className: "source-button",
    text: "前の20件",
    attributes: { type: "button" },
  });
  previous.disabled = scenarioPageIndex === 0;
  previous.addEventListener("click", () => {
    scenarioPageIndex -= 1;
    renderFloodScenario(scenario, context);
  });
  const next = element("button", {
    className: "source-button",
    text: "次の20件",
    attributes: { type: "button" },
  });
  next.disabled = scenarioPageIndex >= pages - 1;
  next.addEventListener("click", () => {
    scenarioPageIndex += 1;
    renderFloodScenario(scenario, context);
  });

  const gisAction =
    !context.isSynthetic && context.regionCode
      ? element("div", {
          className: "scenario-map-action",
          children: [
            element("div", {
              children: [
                element("strong", { text: "地図で確認" }),
                element("p", {
                  text: "選択中の地域をGISで開きます。施設単位の選択情報は付加しません。",
                }),
              ],
            }),
            element("a", {
              className: "gis-cta",
              text: "この地域の地図を開く",
              attributes: { href: buildGisRegionUrl(context.regionCode) },
            }),
          ],
        })
      : null;

  floodScenarioRoot.append(
    ...[
      note,
      summary,
      element("div", {
        className: "scenario-list",
        children: cards.length
          ? cards
          : [
              emptyState(
                "Dのfacility_resultsに施設結果はありません。候補なしとは扱いません。",
              ),
            ],
      }),
      scenarioNotes.length
        ? element("div", { className: "scenario-notes", children: scenarioNotes })
        : null,
      gisAction,
      element("nav", {
        className: "scenario-pagination",
        attributes: { "aria-label": "Scenario施設一覧のページ" },
        children: [
          previous,
          element("span", {
            text: `ページ ${scenarioPageIndex + 1} / ${pages}（このページ ${selected.length}件）`,
          }),
          next,
        ],
      }),
    ].filter(Boolean),
  );
}

function renderOverview(viewModel) {
  const items = [
    ["地域コード", viewModel.regionCode],
    ["対象データ", viewModel.counts.datasets],
    ["できること", viewModel.counts.capabilities],
    ["課題", viewModel.counts.gaps],
    ["改善案", viewModel.counts.recommendations],
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

function renderPage(viewModel) {
  regionName.textContent = viewModel.regionName;
  generatedAt.textContent = viewModel.generatedAt;
  schemaVersion.textContent = viewModel.schemaVersion;
  demoNotice.hidden = !viewModel.isSynthetic;
  setActiveRegion(viewModel.isSynthetic ? null : viewModel.regionCode);

  renderAnalysisSummary(viewModel);
  renderOverview(viewModel);
  scenarioPageIndex = 0;
  renderFloodScenario(viewModel.floodScenario, {
    regionCode: viewModel.regionCode,
    isSynthetic: viewModel.isSynthetic,
  });
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

function clearRegionContent() {
  for (const root of contentRoots) root.replaceChildren();
  if (evidenceDialog.open) evidenceDialog.close();
}

function setActiveRegion(regionCode) {
  for (const button of regionButtons) {
    const isActive = isSelectedRegion(regionCode, button.dataset.regionCode);
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  }
}

function renderLoading(source) {
  clearRegionContent();
  renderFloodScenario({
    uiState: "loading",
    message: `${source.label}の洪水Scenario Resultを取得しています。`,
  });
  setActiveRegion(source.code);
  regionName.textContent = `${source.label}を読み込み中`;
  generatedAt.textContent = "取得中";
  schemaVersion.textContent = "—";
  demoNotice.hidden = true;
  setSourceStatus(`${source.label} のRegionExportを読み込んでいます…`, "loading");
  summaryRoot.append(
    element("div", {
      className: "loading-card",
      children: [
        element("span", {
          className: "loading-dot",
          attributes: { "aria-hidden": "true" },
        }),
        element("span", { text: `${source.label}のRegionExportを読み込んでいます` }),
      ],
    }),
  );
}

function renderError(error, source = null) {
  clearRegionContent();
  renderFloodScenario({
    uiState: "error",
    message: source
      ? `${source.label}のScenario結果を取得できませんでした。古い地域の結果は消去しました。`
      : "Scenario結果を取得できませんでした。古い結果は消去しました。",
  });
  regionName.textContent = source?.label ?? "RegionExport読込失敗";
  generatedAt.textContent = "読込失敗";
  schemaVersion.textContent = "—";
  demoNotice.hidden = true;
  summaryRoot.append(
    element("div", {
      className: "error-card",
      children: [
        element("strong", {
          text: source
            ? `${source.label}のRegionExportを読み込めませんでした。`
            : "RegionExportを表示できませんでした。",
        }),
        element("span", { text: error.message }),
      ],
    }),
  );
}

function setSourceStatus(message, tone = "normal") {
  sourceStatus.textContent = message;
  sourceStatus.dataset.tone = tone;
}

async function fetchRegionExport(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`JSONの取得に失敗しました（HTTP ${response.status}）。`);
  }
  return response.json();
}

function renderLoadedPayload(payload, sourceLabel, expectedRegionCode = null) {
  const regionCode = expectedRegionCode
    ? assertRegionMatches(payload, expectedRegionCode)
    : getPayloadRegionCode(payload);
  regionSelect.value = regionCode;
  renderPage(buildRegionExportViewModel(payload));
  setSourceStatus(`${sourceLabel}｜RegionExportを表示中`, "success");
}

const regionController = createRegionExportController({
  onLoading: renderLoading,
  onSuccess(payload, source) {
    renderLoadedPayload(payload, source.url, source.code);
  },
  onError(error, source) {
    renderError(error, source);
    setSourceStatus(
      `${source.url} を自動読込できませんでした。pipeline出力を生成するか、JSONを手動選択してください。`,
      "error",
    );
  },
});

function loadSelectedRegion() {
  return regionController.selectRegion(regionSelect.value);
}

function selectRegion(regionCode) {
  regionSelect.value = regionCode;
  return regionController.selectRegion(regionCode);
}

async function loadDemoRegionExport() {
  regionController.cancel();
  clearRegionContent();
  setSourceStatus("UI検証用の合成データを読み込んでいます…", "loading");
  try {
    const payload = await fetchRegionExport("./mock/region-export.json");
    renderPage(buildRegionExportViewModel(payload));
    setSourceStatus("mock/region-export.json｜合成デモを表示中", "demo");
  } catch (error) {
    renderError(error instanceof Error ? error : new Error("不明なエラーです。"));
  }
}

closeEvidence.addEventListener("click", () => evidenceDialog.close());
evidenceDialog.addEventListener("click", (event) => {
  if (event.target === evidenceDialog) evidenceDialog.close();
});

regionSelect.addEventListener("change", loadSelectedRegion);
for (const button of regionButtons) {
  button.addEventListener("click", () => selectRegion(button.dataset.regionCode));
}
reloadRegionExport.addEventListener("click", loadSelectedRegion);
loadDemoData.addEventListener("click", loadDemoRegionExport);
regionExportFile.addEventListener("change", async (event) => {
  const [file] = event.target.files ?? [];
  if (!file) return;

  regionController.cancel();
  clearRegionContent();
  setSourceStatus(`${file.name} を読み込んでいます…`, "loading");
  try {
    const payload = JSON.parse(await file.text());
    renderLoadedPayload(payload, file.name);
  } catch (error) {
    const normalized = error instanceof Error ? error : new Error("不明なエラーです。");
    renderError(normalized);
    setSourceStatus(`JSON読込失敗: ${normalized.message}`, "error");
  } finally {
    event.target.value = "";
  }
});

loadSelectedRegion();
