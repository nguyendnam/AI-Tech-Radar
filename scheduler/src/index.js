export const JOBS = {
  "45 23 * * *": "collect-news.yml",
  "30 0 * * *": "daily-digest.yml",
  "0 20 * * 6": "cleanup.yml",
};

export async function dispatchWorkflow(workflow, env) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_OWNER || !env.GITHUB_REPO) {
    throw new Error("Missing GitHub token or repository config");
  }
  const owner = encodeURIComponent(env.GITHUB_OWNER);
  const repo = encodeURIComponent(env.GITHUB_REPO);
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(workflow)}/dispatches`;
  for (let attempt = 1; attempt <= 3; attempt++) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "ai-tech-radar-scheduler",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: env.GITHUB_REF || "main" }),
        signal: AbortSignal.timeout(30000),
      });
    } catch (error) {
      if (attempt === 3) throw error;
    }
    if (response?.ok) {
      console.log(`[OK] ${workflow} dispatched`);
      return;
    }
    if (response && response.status < 500 && response.status !== 429) {
      throw new Error(`GitHub dispatch failed: HTTP ${response.status}`);
    }
    if (attempt === 3) throw new Error(`GitHub dispatch failed: HTTP ${response?.status}`);
    await new Promise(resolve => setTimeout(resolve, attempt * 1000));
  }
}

export default {
  async scheduled(controller, env, ctx) {
    const workflow = JOBS[controller.cron];
    if (!workflow) throw new Error(`Unknown cron: ${controller.cron}`);
    ctx.waitUntil(dispatchWorkflow(workflow, env));
  },
  async fetch(request) {
    if (new URL(request.url).pathname !== "/") return new Response("Not found", { status: 404 });
    return Response.json({ service: "AI Tech Radar Scheduler", status: "ok",
      timezone: "Asia/Ho_Chi_Minh", schedules: {
        collect: "06:45", digest: "07:30", cleanup: "Sunday 03:00",
      },
    });
  },
};
