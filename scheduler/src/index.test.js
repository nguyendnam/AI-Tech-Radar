import test from "node:test";
import assert from "node:assert/strict";
import worker, { JOBS, dispatchWorkflow } from "./index.js";

test("all cron jobs dispatch unified workflows", () => {
  assert.deepEqual(Object.values(JOBS), ["collect-news.yml", "daily-digest.yml", "cleanup.yml"]);
});

test("dispatch uses renamed GitHub owner and configured ref", async () => {
  const original = globalThis.fetch;
  let call;
  globalThis.fetch = async (url, options) => { call = { url, options }; return { ok: true }; };
  try {
    await dispatchWorkflow("collect-news.yml", { GITHUB_OWNER: "nguyendnam", GITHUB_REPO: "AI-Tech-Radar", GITHUB_TOKEN: "test", GITHUB_REF: "main" });
    assert.match(call.url, /repos\/nguyendnam\/AI-Tech-Radar\/actions\/workflows\/collect-news.yml\/dispatches$/);
    assert.deepEqual(JSON.parse(call.options.body), { ref: "main" });
  } finally { globalThis.fetch = original; }
});

test("authentication errors fail without redundant retries", async () => {
  const original = globalThis.fetch;
  let attempts = 0;
  globalThis.fetch = async () => { attempts++; return { ok: false, status: 401 }; };
  try {
    await assert.rejects(dispatchWorkflow("cleanup.yml", { GITHUB_OWNER: "nguyendnam", GITHUB_REPO: "AI-Tech-Radar", GITHUB_TOKEN: "test" }), /401/);
    assert.equal(attempts, 1);
  } finally { globalThis.fetch = original; }
});

test("unknown paths return 404", async () => {
  assert.equal((await worker.fetch(new Request("https://example.com/no"))).status, 404);
});
