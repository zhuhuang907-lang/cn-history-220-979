# cn-history-220-979

公元 220–979 年中国中古史资料库：**三国、两晋、南北朝、隋、唐、五代十国、宋初统一**。
面向历史研究、游戏设计与 LLM（Claude / ChatGPT 等）检索，提供可引用的全文、目录元数据与结构化游戏数据。

- 全文：50 部古籍，2,504 卷，25,227,437 字（约 2,523 万字；中文 Wikisource 转录，古籍原文公有领域）
- 目录：122 条（正史、别史、笔记、类书、制度文献、现代研究、小说、数据库）
- 游戏数据：96 个政权、159 位人物、155 个事件、87 处地点、90 个术语、22 组同名辨析
- 检索：本地 SQLite FTS5 三元组索引，支持繁简通检、按书/时代/可信度过滤

> 本库**不收录现代版权书籍正文**。现代研究仅提供书目元数据与外链；小说/演义标记为 `F`，只能用于叙事与氛围，不得当作史实。

---

## 快速开始

```bash
git clone https://github.com/zhuhuang907-lang/cn-history-220-979.git
cd cn-history-220-979

# 1. 建立全文索引（约 3 分钟，生成 index/search.db，约 300 MB，不纳入 git）
python scripts/build_index.py

# 2. 检索
python scripts/search.py 关羽
python scripts/search.py 节度使 --period 晚唐 --reliability A
python scripts/search.py 燕云十六州 --book JIUWUDAISHI,XINWUDAISHI
python scripts/search.py --catalog 五代 --type primary
python scripts/search.py --game 高平
python scripts/search.py --show SANGUOZHI 36
python scripts/search.py --stats
```

依赖：Python 3.10+，标准库即可；`build_game_data.py` 需要 `jsonschema`。

```bash
pip install jsonschema
python scripts/build_catalog.py
python scripts/build_game_data.py
python scripts/validate.py
python -m unittest discover -s tests
```

---

## 目录结构

```
.
├── data/
│   ├── catalog/                 分类目录源文件（按主题拆分）
│   ├── catalog.json             合并后的 122 条目录
│   ├── catalog_stats.json       统计
│   ├── periods.json             15 个时代段落与游戏钩子
│   ├── factions/                政权分片（96）
│   ├── characters/              人物分片（159）
│   ├── events/                  事件分片（155）
│   ├── locations.json           地点（87，含经纬度）
│   ├── glossary.json            制度/军事/民族/文化术语（90）
│   ├── disambiguation.json      同名辨析（22）
│   ├── game/                    由脚本生成的合并数据（勿手改）
│   └── variants/                OpenCC 繁简对照（Apache-2.0）
├── texts/                       50 部古籍全文，按书分目录、按卷分文件
│   └── index.json               全文字数/卷数索引
├── manifests/
│   └── wikisource_books.json    Wikisource 抓取清单
├── schemas/                     JSON Schema
├── scripts/
│   ├── fetch_wikisource.py      抓取/转换 Wikisource
│   ├── build_catalog.py         合并/校验目录
│   ├── build_game_data.py       合并/校验游戏数据
│   ├── build_index.py           建立 SQLite FTS5 索引
│   ├── search.py                全文/目录/游戏数据检索 CLI
│   ├── validate.py              全库一致性校验
│   └── build_site.py            生成静态检索页数据
├── site/                        GitHub Pages 静态检索页
├── docs/                        方法、目录、游戏设计文档
├── prompts/                     可直接投喂给 Claude 的提示词
├── tests/                       单元测试
├── CLAUDE.md                    Claude 专用使用说明
├── AGENTS.md                    其他编码代理的入口
└── llms.txt                     LLM 友好的资源清单
```

---

## 检索

### 全文检索

```bash
python scripts/search.py <关键词> [选项]
```

| 选项 | 说明 |
|---|---|
| `--book ID[,ID]` | 限定书目，如 `SANGUOZHI`、`JIUWUDAISHI` |
| `--period 时代[,时代]` | 按时代过滤，如 `晚唐`、`五代,十国` |
| `--reliability A[,A/B]` | 按可信度过滤 |
| `--type primary,modern` | 按目录类型过滤 |
| `--limit N` | 返回条数，默认 10 |
| `--context N` | 摘要窗口，默认 70 字 |
| `--json` | 机器可读输出 |

繁简自动通检：输入简体，索引中的繁体原文同样命中；输出保留原文用字。

### 目录 / 游戏数据

```bash
python scripts/search.py --catalog 唐 --period 晚唐
python scripts/search.py --game 安史之乱
python scripts/search.py --list-books
python scripts/search.py --stats
```

### 引用格式

```text
《三国志》卷三十六·蜀书六·关张马黄赵传，Wikisource 转录（CC BY-SA 4.0），
https://zh.wikisource.org/wiki/三國志/卷36
```

`search.py` 会在结果中直接给出书名、卷次、篇名、文件路径与原始链接。

---

## 数据说明

### 目录条目（`data/catalog.json`）

```json
{
  "id": "SANGUOZHI",
  "type": "primary",
  "priority": "core",
  "title": "三国志",
  "title_trad": "三國志",
  "authors": [{"name": "陈寿", "dates": "233–297", "role": "撰"}],
  "periods": ["三国", "西晋"],
  "cover_start": 220,
  "cover_end": 280,
  "reliability": "A",
  "genre": "纪传体正史",
  "fulltext": {"status": "included", "path": "texts/sanguozhi", "volumes_available": 65, "chars": 881434},
  "links": {"wikisource": "https://zh.wikisource.org/wiki/三國志"}
}
```

`fulltext.status`：`included`（全文入库）、`partial`（部分卷）、`external`（仅外链）。

### 游戏数据（`data/game/*.json`）

| 文件 | 内容 |
|---|---|
| `factions.json` | 政权/部族/军阀：起止年、都城、疆域、盟友、敌人、强弱项、游戏钩子 |
| `characters.json` | 人物：生卒、籍贯、所属政权、角色、性格、关系、事件、台词 |
| `events.json` | 事件：年份、类型、地点、参战方、人物、起因/经过/结果/意义 |
| `locations.json` | 地点：今地、经纬度、类型、战略价值 |
| `glossary.json` | 制度、军事、经济、民族、宗教、文化术语 |
| `disambiguation.json` | 同名政权/人物/地名辨析 |
| `periods.json` | 15 个时代段落：摘要、主题、游戏钩子、关键事件 |

事件 `type` 枚举：`war, battle, rebellion, coup, succession, reform, treaty, massacre, migration, disaster, cultural, religious, administrative, diplomatic`。

Schema：`schemas/game-data.schema.json`。源数据按主题分片存放在 `data/factions|characters|events/`，修改后运行：

```bash
python scripts/build_game_data.py
```

### 可信度分级

| 级别 | 含义 | 用法 |
|---|---|---|
| `A` | 正史、原始文献、同时代记录 | 可作为史实依据 |
| `A/B` | 正史但有后世整理/辑佚成分 | 可用，注明版本 |
| `B` | 别史、笔记、方志、私人记述 | 可用，需与 A 级对读 |
| `B/C` | 混合来源、成书较晚 | 谨慎，标注不确定性 |
| `B/F` | 文化史料与志怪/传说混合（如《搜神记》） | 只作民俗、宗教、叙事氛围，不作事实依据 |
| `C` | 类书、总集、后世汇编 | 用于查找线索，不作唯一依据 |
| `M` | 现代研究（版权作品） | 仅书目/外链，不提供正文 |
| `F` | 小说、演义、影视 | 只用于叙事/氛围，不作史实 |
| `D` | 数据库、工具、检索平台 | 作为入口，需回溯原始文献 |

---

## 时代范围

东汉末（184 起）→ 三国（220–280）→ 西晋（266–316）→ 东晋十六国（317–420）→
南北朝（420–589）→ 隋（581–618）→ 初唐/盛唐/中唐/晚唐（618–907）→
五代十国（907–979）→ 宋初统一（960–979）。

详见 `data/periods.json` 与 `docs/catalog.md`。

---

## 版权与来源

- **古籍原文**：公有领域。
- **Wikisource 转录**：CC BY-SA 4.0，署名 Wikisource 贡献者；每个卷文件头部保留来源、修订号、链接与许可。
- **OpenCC 繁简对照表**：Apache-2.0，见 `data/variants/OPENCC-LICENSE.txt`。
- **本项目新增的目录、结构化数据、脚本与文档**：CC BY-SA 4.0（见 `LICENSE`）。
- **现代研究**：仅元数据与外链，不收录正文；引用请遵循原书版权。

如发现版权问题，请开 issue，我们会移除相关内容。

---

## 给 Claude / LLM 使用

1. 先读 `CLAUDE.md`（检索流程、引用规则、输出模板）。
2. 目录与游戏数据可直接读取 JSON；全文检索运行 `python scripts/search.py`。
3. 任何史实结论至少给出一个来源 ID 与卷次；小说（`F`）不得作为论据。
4. 需要构建游戏时，优先使用 `data/game/` 与 `data/periods.json`，再用全文补细节。

`llms.txt` 提供适合爬虫/LLM 的扁平资源清单。

---

## 维护

```bash
# 补抓/更新书目
python scripts/fetch_wikisource.py --book SANGUOZHI --force

# 重建目录与游戏数据
python scripts/build_catalog.py
python scripts/build_game_data.py

# 重建索引与站点
python scripts/build_index.py --force
python scripts/build_site.py

# 全库校验
python scripts/validate.py
python -m unittest discover -s tests
```

## License

CC BY-SA 4.0. See `LICENSE` and `NOTICE.md`.
