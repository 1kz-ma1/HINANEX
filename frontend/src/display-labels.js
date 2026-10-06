const requirementLabels = Object.freeze({
  shelter_location: "避難所位置データ",
});

function getRequirementLabel(requirementCode) {
  return requirementLabels[requirementCode] ?? "対象データ";
}

export { getRequirementLabel };
