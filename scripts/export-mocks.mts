// Exports the frontend mock data to JSON fixtures used to seed the backend.
// Run: node --experimental-strip-types scripts/export-mocks.mts
import { writeFileSync } from "node:fs";
import * as db from "../apps/web/src/api/mock/db.ts";
import * as recon from "../apps/web/src/api/mock/recon.ts";
import * as dashboard from "../apps/web/src/api/mock/dashboard.ts";

const out = "services/api/app/seed/demo"; // shipped inside the API image
const write = (name: string, value: unknown) => writeFileSync(`${out}/${name}.json`, JSON.stringify(value, null, 2) + "\n");
const { copilotAnswer: _fn, ...data } = db;
write("core", data);
write("recon", { ...recon });
write("dashboard", { ...dashboard });
console.log("exported", Object.keys(data).length, "core collections");
