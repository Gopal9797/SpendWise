import { defineConfig } from "@playwright/test";
import path from "node:path";

const e2eDbPath = path.resolve(__dirname, ".e2e", "spendwise-e2e.db");

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: false,
    workers: 1,
    timeout: 60_000,
    expect: {
        timeout: 10_000,
    },
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL: "http://127.0.0.1:8501",
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
        video: "retain-on-failure",
    },
    globalSetup: require.resolve("./e2e/global-setup"),
    webServer: {
        command: "python -m streamlit run app.py --server.headless true --server.port 8501",
        url: "http://127.0.0.1:8501",
        timeout: 120_000,
        reuseExistingServer: false,
        env: {
            SPENDWISE_DB_PATH: e2eDbPath,
        },
    },
});
