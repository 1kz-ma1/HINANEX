function list(value) {
  return Array.isArray(value) ? value : [];
}

function textOrNull(value) {
  return typeof value === "string" && value.trim() ? value : null;
}

function safeHttpUrl(value) {
  const text = textOrNull(value);
  if (!text) return null;

  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function formatDateTime(value) {
  if (!value) return "日時情報なし";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "日時形式を確認してください";

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Tokyo",
  }).format(date);
}

export { formatDateTime, list, safeHttpUrl, textOrNull };
