# FreeToken Radar

Track [OpenRouter](https://openrouter.ai)'s free models — and only trust the ones that are **verified**.

Free-model lineups change without notice: models get delisted, repriced, or quietly swapped. This tool scans the public OpenRouter catalog, diffs it against a hand-verified pool, and tells you exactly what changed.

## The verified pool

A free model enters the pool in `data/verified_pool.json` only when **all** of these hold:

1. Its catalog pricing is zero (prompt **and** completion).
2. Its total parameter count (≥ 100B for the eligible tier) is confirmed from a **vendor-official source** — vendor docs, an official Hugging Face model card, or the paper. Third-party blogs and the model's own *name* are never accepted as evidence.
3. It passes a live tool-calling probe at zero measured cost.

Anything else stays `unverified`, however promising its name looks. Fail closed, always.

Current pool (2026-10-21): **5 eligible** — Inkling (975B) and Inkling Small (276B) by Thinking Machines, NVIDIA Nemotron 3 Ultra 550B, Nemotron 3.5 Super VL 120B, Poolside Laguna S 2.1 (118B).

## Usage

```bash
python3 freetoken_radar.py          # human-readable report
python3 freetoken_radar.py --json   # machine-readable

# Optional live probe of one free model (reads key from env, never from a file):
OPENROUTER_API_KEY=sk-or-... python3 freetoken_radar.py --probe poolside/laguna-s-2.1:free
```

The scan itself needs **no API key** — the catalog endpoint is public. The probe refuses any model ID that is not verified free in the live catalog, because dropping the `:free` suffix can silently route to a paid variant of the same model.

Stdlib only, Python 3.9+.

## 中文说明

追踪 OpenRouter 免费模型变化的命令行工具。核心是一个**人工核验过的模型池**：参数规模必须有厂商官方来源（官方文档 / 官方 HF 模型卡 / 论文）证实、价格全零、且通过零计费的工具调用实测，才算 eligible；其余一律标 unverified——模型名字会骗人，名字不算证据。每日扫描输出：池内模型是否下架/涨价、是否有新的未核验免费模型出现。

## License

MIT
