import { SOURCES, TOPICS, buildComparisonMemo } from "./decision-lab-model.js";

const sourceCards = document.getElementById("sourceCards");
const memo = document.getElementById("memo");
const selectionStatus = document.getElementById("selectionStatus");

for (const source of SOURCES) {
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

function updateMemo() {
  const topic = document.querySelector('input[name="topic"]:checked').value;
  const reviewedIds = [...document.querySelectorAll('input[name="reviewedSource"]:checked')].map((input) => input.value);
  selectionStatus.textContent = "確認目的: " + TOPICS[topic] + "（避難先の自動判断はしません）";
  memo.value = buildComparisonMemo(topic, reviewedIds);
}

document.querySelectorAll('input[name="topic"]').forEach((radio) => {
  radio.addEventListener("change", updateMemo);
});
document.getElementById("makeMemo").addEventListener("click", updateMemo);
sourceCards.addEventListener("change", updateMemo);
updateMemo();
