import { expect, test, type Page } from "@playwright/test";

const consoleErrors = new WeakMap<Page, string[]>();

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  consoleErrors.set(page, errors);
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
});

test.afterEach(async ({ page }) => {
  expect(consoleErrors.get(page) ?? [], "browser console errors").toEqual([]);
});

async function selectContaining(page: Page, label: string, text: string) {
  const select = page.getByLabel(label);
  const value = await select.locator("option").filter({ hasText: text }).getAttribute("value");
  expect(value).toBeTruthy();
  await select.selectOption(value!);
}

async function runAnalysis(page: Page, dataset: string, operation: string) {
  await page.goto("/analysis");
  await selectContaining(page, "Registered dataset", dataset);
  await expect(page.getByLabel("Operation").locator(`option[value="${operation}"]`)).toBeEnabled();
  await page.getByLabel("Operation").selectOption(operation);
  await page.getByRole("button", { name: "Run analysis" }).click();
  await expect(page.getByText("Exact calculation result")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Coverage and limitations" })).toBeVisible();
}

test("application loads with actual API health and dataset portfolio", async ({ page }) => {
  await page.goto("/overview");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("API Healthy", { exact: true })).toBeVisible();
  await expect(page.getByText("Registered datasets")).toBeVisible();
});

test("datasets load and exact dataset detail opens", async ({ page }, testInfo) => {
  await page.goto("/datasets");
  await expect(page.getByText("e2e_sales.csv")).toBeVisible();
  const row = page.getByRole("row").filter({ hasText: "e2e_payables.csv" });
  await row.getByRole("link", { name: "Open" }).click();
  await expect(page.getByRole("heading", { name: "e2e_payables.csv" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Operation-specific readiness" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("dataset-detail-1440.png"), fullPage: true });
});

test("CSV upload progresses through profile, semantics, explicit domain and readiness", async ({ page }, testInfo) => {
  await page.goto("/datasets/new");
  await page.locator('input[type="file"]').setInputFiles({
    name: "web_onboarding_sales.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("Date,Sales\n2026-01-01,10.50\n2026-02-01,20.25\n"),
  });
  await page.getByRole("button", { name: "Upload and profile" }).click();
  await expect(page.getByRole("heading", { name: "Deterministic profile" })).toBeVisible();
  await page.getByRole("button", { name: /Review semantic suggestions/ }).click();
  const evidence = page.getByLabel("Decision evidence");
  await expect(evidence).toHaveValue("");
  await expect(evidence).not.toHaveValue(/Confirmed by dataset owner/i);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.locator(".semantic-card").first()).toBeVisible();
    const pageWidth = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(pageWidth.scrollWidth, `onboarding-${width}: document width ${pageWidth.scrollWidth}px exceeds ${pageWidth.clientWidth}px`).toBeLessThanOrEqual(pageWidth.clientWidth);
    await page.screenshot({ path: testInfo.outputPath(`onboarding-semantics-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await evidence.fill("Synthetic E2E source specification");
  for (const [column, role] of [["Date", "TRANSACTION_DATE"], ["Sales", "SALES"]]) {
    const meaning = page.getByLabel(`Meaning for ${column}`, { exact: true });
    await meaning.selectOption(role);
    const row = page.getByRole("row").filter({ has: meaning });
    if (column === "Date") await row.getByLabel("Date format for Date").selectOption("YYYY-MM-DD");
    await row.getByRole("button", { name: "Confirm semantic role", exact: true }).click();
    await expect(page.getByText("Request not completed")).toHaveCount(0);
  }
  await page.getByRole("button", { name: /Review domain and qualifiers/ }).click();
  let domainMutations = 0;
  let confirmedDomainEvidence: string | undefined;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/domain-confirmation")) {
      domainMutations += 1;
      confirmedDomainEvidence = request.postDataJSON()?.evidence;
    }
  });
  const domain = page.getByLabel("Proposed domain");
  await domain.selectOption("PAYABLE");
  await domain.selectOption("RECEIVABLE");
  expect(domainMutations).toBe(0);
  await domain.selectOption("SALES_RECORD");
  expect(domainMutations).toBe(0);
  await page.getByRole("button", { name: "Confirm domain" }).click();
  await expect(page.getByRole("heading", { name: "Saved domain" })).toBeVisible();
  expect(domainMutations).toBe(1);
  expect(confirmedDomainEvidence).toBe("Synthetic E2E source specification");
  await page.getByRole("button", { name: /Review saved decisions/ }).click();
  await expect(page.getByRole("heading", { name: "Review saved decisions" })).toBeVisible();
  await expect(page.getByText("Sales Record Count")).toBeVisible();
  await expect(page.getByText("Required financial meaning is not confirmed.").first()).toBeVisible();
  await expect(page.getByText("Binding validation returned MISSING_REQUIRED_SEMANTICS.")).toHaveCount(0);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    const pageWidth = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(pageWidth.scrollWidth, `onboarding-review-${width}: document width ${pageWidth.scrollWidth}px exceeds ${pageWidth.clientWidth}px`).toBeLessThanOrEqual(pageWidth.clientWidth);
    await expect(page.getByRole("heading", { name: "Operation readiness" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`onboarding-review-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: /Open operation readiness/ }).click();
  await expect(page.getByText("Sales Record Count")).toBeVisible();
  await expect(page.getByRole("link", { name: /Analyze dataset/ })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("onboarding-ready-1440.png"), fullPage: true });
});

test("multi-sheet XLSX is a bounded clarification and selected sheet uploads", async ({ page }) => {
  await page.goto("/datasets/new");
  await page.locator('input[type="file"]').setInputFiles("/tmp/financial-manager-phase4-e2e/multisheet.xlsx");
  await page.getByRole("button", { name: "Upload and profile" }).click();
  await expect(page.getByRole("heading", { name: "Select workbook sheet" })).toBeVisible();
  // The API intentionally uses HTTP 409 for this bounded clarification. Chromium
  // logs that handled response as a resource error; acknowledge only this expected case.
  expect(consoleErrors.get(page)).toEqual(["Failed to load resource: the server responded with a status of 409 (Conflict)"]);
  consoleErrors.set(page, []);
  await page.getByLabel("Sheet", { exact: true }).selectOption("February");
  await page.getByRole("button", { name: "Upload selected sheet" }).click();
  await expect(page.getByRole("heading", { name: "Deterministic profile" })).toBeVisible();
});

test("SALES_RECORD analysis uses actual HTTP evidence", async ({ page }, testInfo) => {
  await runAnalysis(page, "e2e_sales.csv", "SALES_BY_PERIOD");
  await expect(page.getByRole("img", { name: "Presentation view" })).toBeVisible();
  await expect(page.getByRole("table", { name: "Exact authoritative evidence" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("analysis-sales-1440.png"), fullPage: true });
});

test("PAYABLE analysis uses actual HTTP evidence", async ({ page }) => {
  await runAnalysis(page, "e2e_payables.csv", "PAYABLE_SUMMARY");
});

test("RECEIVABLE analysis uses actual HTTP evidence", async ({ page }) => {
  await runAnalysis(page, "e2e_receivables.csv", "RECEIVABLE_SUMMARY");
});

test("CASH_TRANSACTION analysis uses actual HTTP evidence", async ({ page }) => {
  await runAnalysis(page, "e2e_cash.csv", "CASH_INFLOW_SUMMARY");
});

test("Sales and Profit anomaly screening remain candidate-only", async ({ page }, testInfo) => {
  for (const operation of ["SALES_ANOMALY_SCREEN", "PROFIT_ANOMALY_SCREEN"]) {
    await page.goto("/anomalies");
    await selectContaining(page, "Sales Record dataset", "e2e_sales.csv");
    await expect(page.getByLabel("Measure").locator(`option[value="${operation}"]`)).toBeEnabled();
    await page.getByLabel("Measure").selectOption(operation);
    await page.getByRole("button", { name: "Screen candidates" }).click();
    await expect(page.getByRole("heading", { name: "Candidate table" })).toBeVisible();
    await expect(page.getByText("Statistical candidates for review").first()).toBeVisible();
    await expect(page.getByText(/Fraud detected|Risk score|Likely fraud/)).toHaveCount(0);
  }
  await page.screenshot({ path: testInfo.outputPath("anomalies-profit-1440.png"), fullPage: true });
});

test("chat session sends a question and handles clarification", async ({ page }, testInfo) => {
  await page.goto("/chat");
  const input = page.getByRole("textbox", { name: "Financial question" });
  await expect(input).toBeEnabled();
  await input.fill("How many records are there");
  await page.getByRole("button", { name: "Send financial question" }).click();
  await expect(page.getByText("Clarification required")).toBeVisible();
  const clarification = page.getByLabel("Clarification answer");
  await expect(clarification).toBeVisible();
  await clarification.selectOption({ index: 1 });
  await page.getByRole("button", { name: "Submit clarification" }).click();
  await expect(page.getByText("SUCCESS", { exact: true }).last()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Clarification required" })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("chat-clarification-1440.png"), fullPage: true });
});

test("responsive shell remains usable at all release widths", async ({ page }, testInfo) => {
  const targets = [
    { width: 1440, height: 1000, route: "/overview", name: "overview-1440", title: "Overview — Financial Manager AI" },
    { width: 1024, height: 900, route: "/datasets", name: "datasets-1024", title: "Datasets — Financial Manager AI" },
    { width: 820, height: 1000, route: "/analysis", name: "analysis-820", title: "Analysis — Financial Manager AI" },
    { width: 768, height: 1024, route: "/anomalies", name: "anomalies-768", title: "Anomalies — Financial Manager AI" },
    { width: 390, height: 844, route: "/chat", name: "chat-390", title: "Ask Financial Manager — Financial Manager AI" },
    { width: 320, height: 720, route: "/datasets/new", name: "onboarding-320", title: "Add Dataset — Financial Manager AI" },
  ];
  for (const target of targets) {
    await page.setViewportSize(target);
    await page.goto(target.route);
    await expect(page).toHaveTitle(target.title);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.getByText("API Healthy", { exact: true })).toBeVisible();
    const shellWidth = await page.locator(".app-shell").evaluate((shell) => ({
      clientWidth: shell.clientWidth,
      scrollWidth: shell.scrollWidth,
    }));
    expect(shellWidth.scrollWidth, `${target.name}: application shell width ${shellWidth.scrollWidth}px exceeds ${shellWidth.clientWidth}px`).toBeLessThanOrEqual(shellWidth.clientWidth);
    if (target.width === 1440) {
      await page.keyboard.press("Tab");
      await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.locator("main#main-content")).toBeFocused();
    }
    if (target.width <= 390) {
      const trigger = page.getByRole("button", { name: "Open navigation" });
      await expect(trigger).toBeVisible();
      await trigger.click();
      await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Datasets" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Overview" })).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(trigger).toBeFocused();
      await trigger.click();
      await expect(page.locator(".sidebar")).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, 0)");
    }
    await page.screenshot({ path: testInfo.outputPath(`${target.name}.png`), fullPage: true });
  }
});
