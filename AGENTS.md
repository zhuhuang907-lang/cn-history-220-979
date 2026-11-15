# AGENTS.md

本仓库供编码代理与 LLM 使用。**先读 `CLAUDE.md`**，其中包含完整的检索流程、引用规则、可信度分级与游戏数据模型。

## 快速约定

- 工作目录：仓库根目录。
- Python 3.10+，标准库优先；`build_game_data.py` 需要 `jsonschema`。
- 全文索引是本地构建产物：`python scripts/build_index.py` → `index/search.db`（约 300 MB，不提交）。
- 检索：`python scripts/search.py <关键词>`；目录：`--catalog`；游戏数据：`--game`。
- 源数据在 `data/factions|characters|events/`、`data/locations.json`、`data/glossary.json`、`data/disambiguation.json`；
  `data/game/` 是生成产物，**不要直接编辑**。
- 修改后运行：
  ```bash
  python scripts/build_catalog.py
  python scripts/build_game_data.py
  python scripts/validate.py
  python -m unittest discover -s tests
  ```
- 引用必须带书名、卷次、来源 ID；`F` 级（小说/演义）不得作史实；`M` 级（现代研究）只有书目，不引正文。
- 不要伪造引文、卷次、年份。找不到就说明“未检出”。

## 目录速查

| 需求 | 文件 |
|---|---|
| 书目/可信度/全文状态 | `data/catalog.json` |
| 时代与游戏钩子 | `data/periods.json` |
| 政权 | `data/game/factions.json` |
| 人物 | `data/game/characters.json` |
| 事件 | `data/game/events.json` |
| 地点 | `data/game/locations.json` |
| 术语 | `data/game/glossary.json` |
| 同名辨析 | `data/game/disambiguation.json` |
| Schema | `schemas/game-data.schema.json` |
| 方法说明 | `docs/methodology.md` |
| Claude 手册 | `CLAUDE.md` |
