# Daily "New this week" update (design notes)

`data/new-this-week.json` is separate from `data/tools.json` so a daily job can rewrite it without touching rankings.

Schema: `{updated, note, items:[{date:"YYYY-MM-DD", title, summary, url, type:"model|github|launch"}]}`

Proposed job (not yet implemented / scheduled):
1. **Collect** (once daily, e.g. cron `0 7 * * *` Australia/Sydney):
   - GitHub: `https://github.com/trending?since=daily` and `?since=weekly` (HTML) or GitHub Search API `created:>DATE topic:ai OR topic:llm sort:stars`.
   - Official vendor news feeds/RSS (OpenAI, Anthropic, Google, Mistral, Meta, etc.), Hugging Face trending models, Product Hunt AI category.
2. **Filter**: keep AI-related items; dedupe by URL; drop items older than 7 days.
3. **Verify**: HTTP-check each URL (200, or a known bot-block 403 on an official domain flagged for review). Never invent summaries — derive from the source's own description.
4. **Summarize**: 1–2 sentence writeup from the source text (optionally LLM-assisted, human-reviewable).
5. **Write** the JSON atomically (write tmp, then rename), set `updated`, cap at ~12 items.
6. **Publish**: commit and redeploy the static site (manual step until approved).
