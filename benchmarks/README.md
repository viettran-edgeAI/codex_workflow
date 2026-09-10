# More benchmark coverage

The existing [light benchmark](../light_benchmark/README.md) is a useful first
test of `codex_workflow`. Adding more benchmarks would give a clearer picture of
how well the workflow performs in different situations.

More tests also increase the probability of finding weaknesses and useful
improvements. Different tasks and AI providers may expose problems in routing,
coordination, context handoffs, token usage, or tool use that a single benchmark
cannot reveal.

Useful additions could include:

- different task types, such as bug fixes, features, refactors, and research;
- small and large repositories;
- short tasks and long-context tasks;
- more models and AI providers, including OpenAI, Anthropic, Google, xAI, Z.AI,
  and local/open-weight models;
- comparisons between no workflow and the Light, Medium, and Heavy routes.

To keep comparisons useful, each benchmark should use the same task, prompt,
tools, and acceptance checks whenever possible. Results should record the exact
model, provider, workflow version, completion status, time, and token usage.

This broader coverage could help identify which parts of the workflow already
work well and where future changes would have the greatest impact.
