import path from "node:path";

import { expect, Page, test } from "@playwright/test";

function uniqueSuffix(): string {
    return `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

function escapeRegex(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function openTab(page: Page, tabName: string): Promise<void> {
    await page.getByRole("tab", { name: tabName }).click();
    await expect(page.getByRole("tab", { name: tabName, selected: true })).toBeVisible();
}

async function resetAllTransactionsIfAvailable(page: Page): Promise<void> {
    await openTab(page, "Transactions");

    const deleteAllButton = page.getByRole("button", { name: "Delete all transactions" });
    if ((await deleteAllButton.count()) === 0) {
        return;
    }

    await page
        .getByRole("checkbox", { name: "I understand this will permanently delete all transactions." })
        .setChecked(true, { force: true });
    await deleteAllButton.click();

    await expect(page.getByText("No transactions yet. Add your first transaction above.")).toBeVisible();
}

async function addTransaction(page: Page, category: string, description: string, amount: string): Promise<void> {
    await openTab(page, "Transactions");

    await page.getByRole("spinbutton", { name: "Amount" }).first().fill(amount);
    await page.getByRole("textbox", { name: "Category" }).first().fill(category);
    await page.getByRole("textbox", { name: "Description" }).first().fill(description);
    await page.getByRole("button", { name: "Add Transaction" }).click();

    await expect(page.getByRole("heading", { name: "Edit or Delete Transaction" })).toBeVisible();
}

function selectedTransactionId(textValue: string): number {
    const matched = textValue.match(/^#(\d+)\s\|/);
    if (!matched) {
        throw new Error(`Could not parse transaction id from: ${textValue}`);
    }
    return Number(matched[1]);
}

test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "SpendWise - Personal Expense Tracker" })).toBeVisible();
});

test("dashboard shows core sections", async ({ page }) => {
    await openTab(page, "Dashboard");

    await expect(page.getByRole("heading", { name: "Monthly Snapshot" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Spending by Category" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Spending Trend" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Budget Progress" })).toBeVisible();
});

test("transactions CRUD flow works", async ({ page }) => {
    const suffix = uniqueSuffix();
    const category = `E2E-Cat-${suffix}`;
    const originalDescription = `E2E add ${suffix}`;
    const updatedDescription = `E2E edit ${suffix}`;

    await resetAllTransactionsIfAvailable(page);
    await addTransaction(page, category, originalDescription, "1234");

    await expect(page.getByRole("combobox", { name: "Select Transaction" })).toHaveValue(
        new RegExp(`\\| ${escapeRegex(category)} \\|`)
    );

    await page.getByRole("textbox", { name: "Description" }).last().fill(updatedDescription);
    await page.getByRole("button", { name: "Save Changes" }).click();

    await expect(page.getByRole("textbox", { name: "Description" }).last()).toHaveValue(updatedDescription);

    await resetAllTransactionsIfAvailable(page);
});

test("transaction id keeps incrementing after delete", async ({ page }) => {
    const suffix = uniqueSuffix();

    await resetAllTransactionsIfAvailable(page);

    await addTransaction(page, `ID-A-${suffix}`, `ID-A-${suffix}`, "111");
    const firstSelection = await page.getByRole("combobox", { name: "Select Transaction" }).inputValue();
    const firstId = selectedTransactionId(firstSelection);

    await resetAllTransactionsIfAvailable(page);

    await addTransaction(page, `ID-B-${suffix}`, `ID-B-${suffix}`, "222");
    const secondSelection = await page.getByRole("combobox", { name: "Select Transaction" }).inputValue();
    const secondId = selectedTransactionId(secondSelection);

    expect(secondId).toBeGreaterThan(firstId);
});

test("budget and csv tab flows are accessible", async ({ page }) => {
    const suffix = uniqueSuffix();

    await openTab(page, "Budgets");

    await page.getByRole("textbox", { name: "Category" }).first().fill(`Budget-${suffix}`);
    await page.getByRole("spinbutton", { name: "Budget Amount" }).fill("3000");
    await page.getByRole("button", { name: "Save Budget" }).click();

    await expect(
        page.getByRole("tabpanel", { name: "Budgets" }).getByText(`Budget-${suffix}`).first()
    ).toBeVisible();

    await openTab(page, "CSV Import/Export");

    await page.getByRole("button", { name: "Import CSV" }).click();
    await expect(page.getByText("Please choose a CSV file first.")).toBeVisible();

    const [download] = await Promise.all([
        page.waitForEvent("download"),
        page.getByRole("button", { name: "Download Transactions CSV" }).click(),
    ]);

    expect(download.suggestedFilename()).toContain("spendwise_transactions_");

    const csvPath = path.resolve(__dirname, "..", "data", "demo_transactions.csv");
    await page.locator("input[type='file']").setInputFiles(csvPath);
    await page.getByRole("button", { name: "Import CSV" }).click();

    await openTab(page, "Transactions");
    await expect(page.getByRole("heading", { name: "Edit or Delete Transaction" })).toBeVisible();
});
