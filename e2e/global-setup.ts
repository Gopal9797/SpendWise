import fs from "node:fs";
import path from "node:path";

async function globalSetup(): Promise<void> {
    const e2eDir = path.resolve(__dirname, "..", ".e2e");
    const e2eDbPath = path.join(e2eDir, "spendwise-e2e.db");

    fs.mkdirSync(e2eDir, { recursive: true });

    if (fs.existsSync(e2eDbPath)) {
        fs.rmSync(e2eDbPath, { force: true });
    }
}

export default globalSetup;
