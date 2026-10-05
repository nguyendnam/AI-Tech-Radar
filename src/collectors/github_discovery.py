import time
from datetime import (
    date,
    timedelta,
)

from src.http import github_session
from src.profile import (
    load_profile,
)

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"


def collect_github_repositories() -> list[dict]:

    profile = load_profile()

    searches = profile.get(
        "github_searches",
        [],
    )

    limit = int(
        profile.get(
            "limits",
            {},
        ).get(
            "github_results_per_query",
            5,
        )
    )

    # Chỉ tìm repo được tạo trong
    # 7 ngày gần nhất.

    created_after = (date.today() - timedelta(days=7)).isoformat()

    session = github_session()

    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-tech-radar",
        }
    )

    results = {}

    for search in searches:
        query = f"{search['query']} created:>={created_after}"

        try:
            response = session.get(
                GITHUB_SEARCH_API,
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": limit,
                },
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            for repo in data.get(
                "items",
                [],
            ):
                full_name = repo["full_name"]

                candidate = {
                    "source_platform": "github",
                    "external_id": f"repo:{full_name}",
                    "item_type_hint": search.get(
                        "type",
                        "GITHUB_REPO",
                    ),
                    "name": full_name,
                    "title": full_name,
                    "description": (repo.get("description") or ""),
                    "url": (repo.get("html_url") or ""),
                    "published_at": repo.get("created_at"),
                    "metadata": {
                        "stars": repo.get(
                            "stargazers_count",
                            0,
                        ),
                        "forks": repo.get(
                            "forks_count",
                            0,
                        ),
                        "open_issues": repo.get(
                            "open_issues_count",
                            0,
                        ),
                        "language": repo.get("language"),
                        "topics": repo.get(
                            "topics",
                            [],
                        ),
                        "license": (repo.get("license") or {}).get("spdx_id"),
                        "owner": (repo.get("owner") or {}).get("login"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                    },
                }

                old = results.get(full_name)

                if (
                    old is None
                    or candidate["metadata"]["stars"] > old["metadata"]["stars"]
                ):
                    results[full_name] = candidate

        except Exception as exc:
            print(f"[WARN] GitHub search {query}: {exc}")

        # Tránh đập Search API quá nhanh.
        time.sleep(7)

    return list(results.values())
