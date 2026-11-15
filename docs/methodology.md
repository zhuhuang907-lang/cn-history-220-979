# 方法说明

本文件记录 `cn-history-220-979` 的资料范围、选书标准、文本处理流程、可信度分级与已知局限。目标是让研究者、游戏设计师与 LLM 都能判断“这条信息从哪来、有多可靠、该怎么用”。

---

## 1. 范围与时代划分

### 1.1 时间范围

主体为 **220–979 年**：

- 三国（220–280）
- 西晋（266–316）
- 东晋十六国（317–420）
- 南北朝（420–589）
- 隋（581–618）
- 唐（618–907），细分为初唐、盛唐、中唐、晚唐
- 五代十国（902–979）
- 宋初统一（960–979）

为交代前因后果，目录可上溯至**东汉末（184 年起）**，下延至**宋初**。这些衔接条目在目录中单独标注时代，不与主体混淆。

### 1.2 为什么断在 979

979 年北宋灭北汉，传统上被视为五代十国分裂局面的终结。此前的陈桥兵变（960）、后蜀/南汉/南唐/吴越的归宋，均作为“宋初统一”段落处理。

### 1.3 地理范围

以传统“中国”历史地理为主，兼顾：

- 中原、关中、河北、河东、江淮、江南、巴蜀、荆楚、岭南、福建
- 北方与西北民族政权：匈奴、鲜卑、羯、氐、羌、柔然、突厥、回鹘、吐蕃、契丹等
- 东北：高句丽、渤海、契丹
- 西域：西域都护府故地、高昌、于阗、龟兹等

地名以史料中的政区名为准，现代坐标仅作游戏地图参考。

---

## 2. 选书标准

目录条目分四类：

| 类型 | 说明 | 例子 |
|---|---|---|
| `primary` | 古籍、正史、编年史、政书、别史、笔记、类书、总集、金石碑志 | 《三国志》《资治通鉴》《唐六典》 |
| `modern` | 现代研究著作（仅元数据与外链） | 田余庆《东晋门阀政治》 |
| `fiction` | 小说、演义、影视/游戏设定 | 《三国演义》《残唐五代史演义》 |
| `database` | 数据库、工具书、地图集、检索平台 | CBDB、CTEXT |

### 2.1 收录优先级

- **core**：研究或游戏设计绕不开的核心史料。
- **extended**：重要补充，覆盖特定政权、制度、地区或文体。
- **reference**：工具书、类书、数据库、延伸阅读。

### 2.2 不收什么

- 现代版权书籍正文、译注、点校本的大段正文；
- 来源不明、版本不清的网络文本；
- 纯文学创作中与历史无关的部分；
- 无法核实作者、成书年代或版本的信息。

### 2.3 版本与成书年代

- 古籍以常见传世版本为准，优先采用 Wikisource 已校对文本。
- `date` 为成书或大致成书年代，不是作者生卒年。
- 正史存在后世整理、辑佚、注释层，目录中用 `A/B` 或 `B/C` 标注。
- 同一史事尽量保留多种史料，便于对读，而不是只留“标准答案”。

---

## 3. 可信度分级

| 级别 | 定义 | 典型材料 | 使用规则 |
|---|---|---|---|
| `A` | 正史、编年史、政书、同时代原始文献 | 《三国志》《旧唐书》《唐会要》 | 可作为史实依据，仍需注意立场与回护 |
| `A/B` | 基本可靠，但有后世辑佚、整理、删润 | 部分辑本、后世补修 | 可用，注明版本与整理者 |
| `B` | 别史、方志、笔记、文集、碑志 | 《十国春秋》《唐语林》 | 可用，需与 A 级对读 |
| `B/C` | 混合来源、成书较晚、转引较多 | 后世汇编、类书 | 谨慎，标注不确定性 |
| `B/F` | 文化史料与志怪/传说混合 | 《搜神记》 | 只作民俗、宗教、叙事氛围，不作事实依据 |
| `C` | 类书、总集、后世考证 | 《太平御览》类 | 只作线索，回溯原始出处 |
| `M` | 现代研究（版权作品） | 学术专著、论文 | 只引书目/外链，不引正文 |
| `F` | 小说、演义、影视、游戏设定 | 《三国演义》 | 只用于叙事/氛围，不作史实 |
| `D` | 数据库、工具书、地图集 | CBDB、CTEXT | 作入口，回溯原始文献 |

### 3.1 冲突处理

1. 优先采用时代更早、史源更近的记载。
2. 正史之间冲突时，比较成书年代、作者立场、是否亲历、是否有档案依据。
3. 笔记、类书、方志只作补充；能回溯到正史或原始文书时，以原始出处为准。
4. 无法判断时，保留异说，写“一说”“约”“传”，不伪造精确结论。

### 3.2 游戏数据中的可信度

`data/game/` 的条目均带 `reliability`。当前结构化数据以 `A` 级为主，但**游戏化描述**（如“高统率”“低外交”）是设计抽象，不是史料原文。引用时应区分：

- **史实层**：人物、事件、年份、地点、来源 ID；
- **设计层**：数值、标签、强弱项、游戏钩子。

---

## 4. 全文获取与处理

### 4.1 来源

全文来自[中文 Wikisource](https://zh.wikisource.org/)。选择理由：

- 古籍原文公有领域；
- 社区持续校对，保留修订历史；
- 提供 API，可按页面抓取 wikitext 或渲染 HTML；
- 许可清晰（CC BY-SA 4.0）。

### 4.2 抓取流程

`scripts/fetch_wikisource.py`：

1. 读取 `manifests/wikisource_books.json` 中的书目与卷目。
2. 调用 MediaWiki API `action=parse` 获取 wikitext、revid、displaytitle。
3. 若页面正文由 ProofreadPage 的 `<pages index="..." />` 转写，则改抓渲染 HTML（`prop=text`），因为 wikitext 只有目录。
4. 将 HTML 转为纯文本，去除导航、脚注标记、编辑链接等。
5. 写入 `texts/<slug>/卷NNN.txt`，卷首保留来源、修订号、许可、抓取日期与原始链接。
6. 生成 `manifest.json` 与全局 `texts/index.json`。

### 4.3 文本清理

- 去除页眉页脚、前后卷导航（`◄`、`►`、`姊妹計劃`、`維基百科條目` 等）。
- 去除编辑链接、脚注编号、残留 HTML 标签。
- 保留原文异体字、避讳字、夹注（`〈……〉`）与篇名。
- 不做现代标点重排，不把繁体强转为简体；简体仅用于检索映射。

### 4.4 卷文件格式

```text
# 三國志 卷036 · 蜀書六

> 来源：Wikisource《三國志/卷36》
> 修订号：123456
> 许可：CC BY-SA 4.0（Wikisource 贡献者整理；古籍原文为公有领域）
> 抓取日期：2026-11-14
> 原始链接：https://zh.wikisource.org/wiki/三國志/卷36

---

正文……
```

- `#` 行为书名与卷次，便于机器解析。
- `>` 行为溯源元数据，引用时只引 `---` 之后的正文。
- 分上下卷的文件名形如 `卷017下.txt`，引用时保留“下”。

### 4.5 已知文本问题

- 转录仍可能有错字、漏字、断句错误；重要引文请对照 Wikisource 原页面或纸本。
- 部分卷目依赖社区转录，可能缺卷、重卷或篇名不全。
- 繁简转换只用于检索，不改变原文；输出保留繁体。
- 个别页面含表格、目录或列表，转换为纯文本后层级可能丢失。

---

## 5. 目录数据

### 5.1 源文件与生成物

- 源文件：`data/catalog/*.json`，按主题分片，便于人工维护。
- 生成物：`data/catalog.json`、`data/catalog_stats.json`、`docs/catalog.md`、`site/data/catalog.json`。
- 修改源文件后运行：

  ```bash
  python scripts/build_catalog.py
  ```

- CI 用 `python scripts/build_catalog.py --check` 检查生成物是否过期。

### 5.2 字段约定

| 字段 | 说明 |
|---|---|
| `id` | 大写稳定标识，如 `SANGUOZHI`、`JIUWUDAISHI` |
| `type` | `primary` / `modern` / `fiction` / `database` |
| `priority` | `core` / `extended` / `reference` |
| `periods` | 目录时代词表，含 `宋初`、`跨期` 等 |
| `cover_start` / `cover_end` | 内容覆盖年代，不是成书年 |
| `reliability` | A / A/B / B / B/C / C / M / F / D |
| `fulltext.status` | `included` / `partial` / `external` |
| `fulltext.path` | 库内全文目录，如 `texts/sanguozhi` |
| `links` | Wikisource、CTEXT、出版社等外链 |

### 5.3 时代词表

目录使用：

```text
先秦, 秦汉, 两汉, 东汉末, 三国, 西晋, 东晋, 两晋, 魏晋,
十六国, 南朝, 北朝, 南北朝, 隋, 唐, 初唐, 盛唐, 中唐,
晚唐, 五代, 十国, 宋, 宋初, 跨期
```

游戏数据使用 `data/periods.json` 的 15 个名称，其中统一用 **`宋初统一`**，不使用目录里的 `宋初`。两套词表服务不同目的，不要混用。

---

## 6. 游戏数据

### 6.1 设计目标

把史料转成**可检索、可引用、可扩展**的游戏设定数据，而不是写死一套数值：

- 每个实体有稳定 `id`，便于程序引用；
- 每条数据带 `sources` 与 `reliability`，便于回溯；
- 事件类型、地点类型、术语分类使用固定枚举；
- 数值与强弱项是设计建议，可按玩法调整。

### 6.2 源文件与生成物

源文件：

```text
data/periods.json
data/factions/*.json
data/characters/*.json
data/events/*.json
data/locations.json
data/glossary.json
data/disambiguation.json
```

生成物：

```text
data/game/factions.json
data/game/characters.json
data/game/events.json
data/game/locations.json
data/game/glossary.json
data/game/disambiguation.json
data/game/periods.json
data/game/index.json
```

修改源文件后运行：

```bash
python scripts/build_game_data.py
```

脚本会做 schema 校验、ID 唯一性检查、引用完整性检查，并输出 `ERROR` / `WARNING`。`data/game/` 是生成产物，不要直接编辑。

### 6.3 Schema

`schemas/game-data.schema.json` 定义六类实体：

- `faction`：政权、部族、军阀、起义军、边镇
- `character`：人物
- `event`：事件
- `location`：地点
- `glossary`：制度、军事、经济、社会、民族、宗教、文化、地理、官称、法律术语
- `disambiguation`：同名政权/人物/地名辨析

事件 `type` 枚举：

```text
war, battle, rebellion, coup, succession, reform, treaty, massacre,
migration, disaster, cultural, religious, administrative, diplomatic
```

### 6.4 引用规则

- `factions`、`characters`、`location_id`、`events` 必须引用已存在的 `id`。
- `sources` 必须引用 `data/catalog.json` 中存在的书目 `id`。
- `relationships[].target` 指向人物 `id`；缺失时脚本给 `WARNING`，不阻断构建。
- 新增实体时，先加目录条目（若需要新史料），再加游戏数据，最后重建。

---

## 7. 全文索引

### 7.1 技术方案

`scripts/build_index.py`：

- 使用 SQLite **FTS5**，`tokenize='trigram'`，支持中文任意子串检索；
- 用 OpenCC `TSCharacters.txt` 建立繁→简字符映射，查询时把输入转成简体，索引中同时存原文与简体形式；
- 生成 `index/search.db`（约 300 MB）与 `index/volumes.jsonl`、`index/build_info.json`；
- `index/` 不提交 git，由使用者本地构建。

### 7.2 检索策略

- 3 字及以上：FTS5 trigram。
- 2 字：SQLite `LIKE` 扫描（trigram 对 2 字查询效果差）。
- 1 字：不建议，结果过泛。
- 支持按书、时代、可信度、类型过滤。
- 输出保留原文繁体，摘要做繁简归一后定位。

### 7.3 局限

- trigram 索引体积大，首次构建约 3 分钟（视机器而定）。
- 繁简映射是字符级，异体字、通假字、古今字仍可能漏检。
- 索引不包含现代研究正文（本来就没有），也不包含图像、表格结构。
- 重建索引会反映最新文本；如果只改目录或游戏数据，不需要重建全文索引。

---

## 8. 校验与测试

```bash
python scripts/build_catalog.py --check
python scripts/build_game_data.py
python scripts/validate.py
python -m unittest discover -s tests
```

`scripts/validate.py` 检查：

- 目录源与生成物是否一致；
- `fulltext` 路径、卷数、字数与 `texts/index.json` 是否一致；
- 游戏数据 schema、ID 唯一性、引用完整性；
- 站点数据副本是否与源数据一致；
- 必要文件是否存在。

测试覆盖目录、游戏数据、文本索引、检索工具与站点构建。CI 不构建 300 MB 全文索引；涉及全文检索的测试在索引缺失时跳过。

---

## 9. 已知局限

1. **版本差异**：同一史书有多个版本，标点、篇名、卷次可能不同。
2. **转录错误**：自动抓取与社区转录都可能出错，重要引文需复核。
3. **系年问题**：古籍年份、月份、日食记录可能有误；游戏数据中的年份是通行系年。
4. **地名古今**：现代坐标是近似值，历史政区边界与今制不同。
5. **民族与政权标签**：使用历史语境中的称谓，不意味着认同其价值判断。
6. **数字夸张**：兵力、户数、人口常被夸大，引用时注明“史载”。
7. **覆盖不均**：五代十国、南朝、北朝材料较丰富；十六国、十国部分政权材料依赖后世汇编。
8. **游戏化抽象**：强弱项、数值、关系标签是设计建议，不是史学结论。

---

## 10. 版权政策

- 古籍原文：公有领域。
- Wikisource 转录：CC BY-SA 4.0，署名 Wikisource 贡献者。
- 本项目新增目录、数据、脚本、文档、站点：CC BY-SA 4.0。
- 现代研究：仅书目元数据与外链，不收录正文。
- 小说/演义：标 `F`，只用于叙事与氛围。

详见 [`LICENSE`](../LICENSE) 与 [`NOTICE.md`](../NOTICE.md)。

---

## 11. 如何新增一本书

1. 在 `data/catalog/<主题>.json` 添加条目，填写 `id`、`type`、`periods`、`reliability`、`links` 等。
2. 如需全文，在 `manifests/wikisource_books.json` 添加书目与卷目，运行：

   ```bash
   python scripts/fetch_wikisource.py --book NEWBOOK_ID
   ```

3. 更新目录条目的 `fulltext`（`status`、`volumes_available`、`chars`）。
4. 运行 `python scripts/build_catalog.py`。
5. 运行 `python scripts/build_index.py --force`（全文有变化时）。
6. 运行 `python scripts/validate.py` 与测试。

## 12. 如何新增游戏数据

1. 确认实体 `id` 唯一、使用小写连字符。
2. 在对应源文件添加条目，填写 `sources` 与 `reliability`。
3. 事件必须使用 schema 枚举的 `type`，并引用已存在的 `faction` / `character` / `location`。
4. 运行 `python scripts/build_game_data.py`，修复所有 `ERROR`。
5. 运行 `python scripts/validate.py` 与测试。

---

## 13. 版本与变更

- 生成物（`data/catalog.json`、`data/game/*.json`、`site/data/*`）应随源文件一起提交。
- 全文抓取记录修订号；如需复现某一版本，可依修订号回溯 Wikisource。
- 索引是本地产物，不纳入版本控制；换机器后重新构建即可。
