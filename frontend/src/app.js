import { buildCapabilityViewModel, formatDateTime } from "./capability-view-model.js";

const root = document.querySelector("#capabilityRoot");
const regionName = document.querySelector("#regionName");
const generatedAt = document.querySelector("#generatedAt");
const schemaVersion = document.querySelector("#schemaVersion");
const evidenceDialog = document.querySelector("#evidenceDialog");
const evidenceBody = document.querySelector("#evidenceBody");
const closeEvidence = document.querySelector("#closeEvidence");

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

function dependencyCard(dependency) {
  const head = element("div", {
    className: "dependency-head",
    children: [
      element("span", { className: "dependency-code", text: dependency.requirementCode }),
      statusBadge(dependency.statusLabel, dependency.tone, "dependency-status"),
    ],
  });

  const reason = dependency.reasons.length
    ? dependency.reasons.join(" ")
    : "依存データの評価理由は提供されていません。";

  return element("article", {
    className: "dependency-item",
    children: [
      head,
      element("div", {
        className: "dependency-criticality",
        text: `Capability内の重要度：${dependency.criticality}`,
      }),
      element("p", { className: "dependency-reason", text: reason }),
    ],
  });
}

function definitionRow(term, value) {
  return [element("dt", { text: term }), element("dd", { text: value ?? "情報なし" })];
}

function evidenceCard(evidence) {
  const details = element("dl", { className: "evidence-data" });
  details.append(
    ...definitionRow("提供元", evidence.publisher),
    ...definitionRow("公開日時", evidence.publishedAt ? formatDateTime(evidence.publishedAt) : null),
    ...definitionRow("取得日時", evidence.fetchedAt ? formatDateTime(evidence.fetchedAt) : null),
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

  return element("article", {
    className: "evidence-item",
    children: [
      element("h3", { text: evidence.sourceName }),
      element("p", { text: `requirement_code: ${evidence.requirementCode}` }),
      details,
    ],
  });
}

function openEvidence(evidence) {
  evidenceBody.replaceChildren();

  if (!evidence.length) {
    evidenceBody.append(
      element("p", {
        text: "このCapabilityに紐づくEvidenceはRegionExportに含まれていません。",
      }),
    );
  } else {
    evidenceBody.append(...evidence.map(evidenceCard));
  }

  evidenceDialog.showModal();
}

function renderCapability(viewModel) {
  regionName.textContent = viewModel.regionName;
  generatedAt.textContent = `出力生成：${viewModel.generatedAt}`;
  schemaVersion.textContent = `Contract ${viewModel.schemaVersion}`;

  const top = element("div", {
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
  });

  const reasonSection = element("section", {
    className: "card-section",
    children: [
      element("div", { className: "section-label", text: "評価理由" }),
      reasonList(viewModel.reasons, "Capabilityの評価理由は提供されていません。"),
    ],
  });

  const dependencyContent = viewModel.dependencies.length
    ? viewModel.dependencies.map(dependencyCard)
    : [element("p", { className: "dependency-reason", text: "依存データ情報はありません。" })];

  const dependencySection = element("section", {
    className: "card-section",
    children: [
      element("div", { className: "section-label", text: "依存データ" }),
      element("div", { className: "dependency-list", children: dependencyContent }),
    ],
  });

  const evidenceButton = element("button", {
    className: "primary-button",
    text: `Evidenceを見る（${viewModel.evidence.length}件）`,
    attributes: { type: "button" },
  });
  evidenceButton.addEventListener("click", () => openEvidence(viewModel.evidence));

  const bottom = element("div", {
    className: "card-bottom",
    children: [
      element("p", {
        className: "assessed-at",
        text: `評価日時：${viewModel.assessedAt} / Engine ${viewModel.engineVersion}`,
      }),
      element("div", { className: "card-actions", children: [evidenceButton] }),
    ],
  });

  const card = element("article", {
    className: `capability-card tone-${viewModel.tone}`,
    attributes: { "data-status": viewModel.statusCode },
    children: [
      top,
      element("div", { className: "card-grid", children: [reasonSection, dependencySection] }),
      bottom,
    ],
  });

  root.replaceChildren(card);
}

function renderError(error) {
  root.replaceChildren(
    element("div", {
      className: "error-card",
      children: [
        element("strong", { text: "RegionExportを表示できませんでした。" }),
        element("span", { text: error.message }),
      ],
    }),
  );
}

async function loadRegionExport() {
  const response = await fetch("./mock/region-export.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`JSONの取得に失敗しました（HTTP ${response.status}）。`);
  }

  return response.json();
}

closeEvidence.addEventListener("click", () => evidenceDialog.close());
evidenceDialog.addEventListener("click", (event) => {
  if (event.target === evidenceDialog) evidenceDialog.close();
});

try {
  const exportData = await loadRegionExport();
  renderCapability(buildCapabilityViewModel(exportData));
} catch (error) {
  renderError(error instanceof Error ? error : new Error("不明なエラーです。"));
}
