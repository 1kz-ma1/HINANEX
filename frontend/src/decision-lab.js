import { SOURCES, TOPICS, RESEARCH_QUESTIONS, buildComparisonMemo, buildEvidenceComparison } from "./decision-lab-model.js";

const sourceCards = document.getElementById("sourceCards");
const memo = document.getElementById("memo");
const selectionStatus = document.getElementById("selectionStatus");
const researchQuestion = document.getElementById("researchQuestion");
const leftSource = document.getElementById("leftSource");
const rightSource = document.getElementById("rightSource");
const comparisonRoot = document.getElementById("comparisonRoot");
const compareWarning = document.getElementById("compareWarning");

function appendOption(select, value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  select.append(option);
}

for (const [id, question] of Object.entries(RESEARCH_QUESTIONS)) {
  appendOption(researchQuestion, id, question.title);
}
for (const source of SOURCES) {
  appendOption(leftSource, source.id, source.title);
  appendOption(rightSource, source.id, source.title);

  const article = document.createElement("article");
  article.className = "source-card";
  const heading = document.createElement("h3");
  heading.textContent = source.title;
  const description = document.createElement("p");
  description.textContent = source.description;
  const scope = document.createElement("p");
  scope.className = "scope";
  scope.textContent = source.scope;
  const link = document.createElement("a");
  link.href = source.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "公式の原文を開く ↗";
  const reviewLabel = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = source.id;
  checkbox.name = "reviewedSource";
  const caption = document.createElement("span");
  caption.textContent = "自分で原文を確認した（自己申告）";
  reviewLabel.append(checkbox, caption);
  article.append(heading, description, scope, link, reviewLabel);
  sourceCards.append(article);
}

leftSource.value = "wide";
rightSource.value = "waiting";

function sourceColumn(source) {
  const article = document.createElement("article");
  article.className = "compare-card";
  const heading = document.createElement("h3");
  heading.textContent = source.title;
  const intro = document.createElement("p");
  intro.textContent = source.description;
  const scopeTitle = document.createElement("strong");
  scopeTitle.textContent = "この資料の説明対象";
  const scope = document.createElement("p");
  scope.textContent = source.scope;
  const link = document.createElement("a");
  link.href = source.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "一次資料を開いて照合 ↗";
  article.append(heading, intro, scopeTitle, scope, link);
  return article;
}

function renderComparison(pair) {
  comparisonRoot.replaceChildren();
  const question = document.createElement("p");
  question.className = "compare-question";
  question.textContent = "確認の視点: " + pair.prompt;
  const columns = document.createElement("div");
  columns.className = "compare-columns";
  columns.append(sourceColumn(pair.left), sourceColumn(pair.right));
  const gap = document.createElement("p");
  gap.className = "compare-gap";
  const strong = document.createElement("strong");
  strong.textContent = "この比較ではまだ分からないこと";
  const description = document.createElement("span");
  description.textContent = pair.unresolved;
  gap.append(strong, description);
  comparisonRoot.append(question, columns, gap);
}

function updateMemo() {
  const topic = document.querySelector('input[name="topic"]:checked').value;
  const reviewedIds = [...document.querySelectorAll('input[name="reviewedSource"]:checked')].map((input) => input.value);
  selectionStatus.textContent = "確認目的: " + TOPICS[topic] + "（避難先の自動判断はしません）";

  let comparison = null;
  try {
    comparison = {
      questionId: researchQuestion.value,
      leftId: leftSource.value,
      rightId: rightSource.value,
    };
    const pair = buildEvidenceComparison(comparison.questionId, comparison.leftId, comparison.rightId);
    compareWarning.textContent = "";
    renderComparison(pair);
  } catch (error) {
    comparison = null;
    comparisonRoot.replaceChildren();
    compareWarning.textContent = error.message + "。施設の比較・判定は行っていません。";
  }
  memo.value = buildComparisonMemo(topic, reviewedIds, comparison);
}

document.querySelectorAll('input[name="topic"]').forEach((radio) => {
  radio.addEventListener("change", updateMemo);
});
for (const input of [researchQuestion, leftSource, rightSource]) {
  input.addEventListener("change", updateMemo);
}
document.getElementById("makeMemo").addEventListener("click", updateMemo);
sourceCards.addEventListener("change", updateMemo);
updateMemo();
