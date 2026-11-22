export function displayDecimal(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return typeof value === "string" ? value : String(value);
}

export function displayMoney(
  value: string | null | undefined,
  currency: { status?: string; state?: string; code?: string | null } | null | undefined,
): string {
  const exact = displayDecimal(value);
  const state = currency?.status || currency?.state;
  if (state === "CONFIRMED" && currency?.code) return `${currency.code} ${exact}`;
  if (state === "CONFIRMED_MULTIPLE") return `${exact} · mixed confirmed currencies`;
  return `${exact} · unverified source denomination`;
}

export function displayCurrencyState(state: string, code?: string | null): string {
  if (state === "CONFIRMED" && code) return code;
  if (state === "CONFIRMED_MULTIPLE") return "Mixed confirmed currencies";
  return "Unverified source denomination";
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function humanize(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
