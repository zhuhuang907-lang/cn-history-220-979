# CLAUDE.md

本文件是 Claude（或其他 LLM）使用本仓库的**操作手册**。目标：在 220–979 年中国中古史范围内，快速、可追溯地检索史料，并把结果转化为游戏设定。

---

## 1. 先做什么

任何任务开始前，按顺序确认：

1. **范围**：用户问的是哪个时代、哪一政权、哪个人物？
2. **查目录**：`data/catalog.json` 里有哪些书覆盖这个主题？可信度如何？
3. **查结构化数据**：`data/game/` 是否已有政权/人物/事件/地点条目？
4. **查全文**：运行 `python scripts/search.py` 找原文；不要凭记忆编造引文。
5. **标注来源**：每条史实结论附 `来源ID + 书名 + 卷次`。

> 禁止把小说、影视、游戏设定当作史实。`reliability: F` 只能用于氛围、人物气质、叙事母题。

---

## 2. 仓库地图

| 路径 | 用途 |
|---|---|
| `data/catalog.json` | 122 条书目元数据（类型、时代、可信度、全文状态、外链） |
| `data/catalog/` | 目录源分片，按主题拆分 |
| `texts/<slug>/卷NNN.txt` | 古籍全文，繁体原文，卷首含来源与许可 |
| `texts/index.json` | 全文书目索引（卷数、字数） |
| `data/periods.json` | 15 个时代段落：摘要、主题、游戏钩子、关键事件 |
| `data/game/factions.json` | 政权/部族/军阀 |
| `data/game/characters.json` | 人物 |
| `data/game/events.json` | 事件 |
| `data/game/locations.json` | 地点（含经纬度） |
| `data/game/glossary.json` | 制度/军事/民族/文化术语 |
| `data/game/disambiguation.json` | 同名辨析 |
| `schemas/` | JSON Schema |
| `scripts/search.py` | 全文/目录/游戏数据检索 |
| `scripts/build_index.py` | 建立 SQLite FTS5 索引 |
| `scripts/build_game_data.py` | 合并并校验游戏数据 |
| `docs/` | 方法、目录、游戏设计文档 |
| `prompts/` | 可复用的提示词 |

---

## 3. 检索流程

### 3.1 全文检索

```bash
python scripts/search.py "关键词" --limit 10
python scripts/search.py "关键词" --book SANGUOZHI,JINSHU
python scripts/search.py "关键词" --period 晚唐 --reliability A
python scripts/search.py "关键词" --json
```

- 繁简自动通检：输入简体即可命中繁体原文。
- 2 字关键词走 LIKE 扫描；3 字及以上走 FTS5 trigram。
- `--json` 返回 `book_id / book_title / volume / section / path / url / snippet / hits`。

### 3.2 按书查卷

```bash
python scripts/search.py --show SANGUOZHI 36
python scripts/search.py --list-books
```

### 3.3 目录检索

```bash
python scripts/search.py --catalog 节度使 --period 晚唐
python scripts/search.py --catalog 五代 --type primary --reliability A
```

### 3.4 游戏数据检索

```bash
python scripts/search.py --game 高平
python scripts/search.py --game 安禄山 --json
```

### 3.5 直接读文件

- 全文：`texts/sanguozhi/卷036.txt`
- 目录：`data/catalog.json`
- 游戏数据：`data/game/*.json`

卷文件结构：

```
# 三國志 卷036 · 蜀書六
> 来源：Wikisource《三國志/卷36》
> 修订号：...
> 许可：CC BY-SA 4.0 ...
> 原始链接：...
---
正文……
```

引用时只引 `---` 之后的正文；卷首元数据用于溯源。

---

## 4. 引用格式

### 4.1 标准格式

```text
《三国志》卷三十六·蜀书六·关张马黄赵传，
Wikisource 转录（CC BY-SA 4.0），
https://zh.wikisource.org/wiki/三國志/卷36
```

### 4.2 带原文

```text
《三国志》卷三十六：“先主与二人寝则同床，恩若兄弟。”
（SANGUOZHI，texts/sanguozhi/卷036.txt）
```

### 4.3 规则

- 必须给出**书名 + 卷次**；有篇名则加篇名。
- 必须给出**来源 ID**（如 `SANGUOZHI`），便于程序回溯。
- 现代研究只引书目信息，不引正文。
- 小说/演义引文必须标注 `F`，并说明“非史实”。
- 不确定的年份、人物关系，写“约”“传”“一说”，不要伪造精确数字。

---

## 5. 可信度规则

| 级别 | 含义 | 允许的用法 |
|---|---|---|
| `A` | 正史、原始文献、同时代记录 | 直接作为史实依据 |
| `A/B` | 正史但有后世辑佚/整理 | 可用，注明版本 |
| `B` | 别史、笔记、方志、私人记述 | 可用，需与 A 级对读 |
| `B/C` | 混合来源、成书较晚 | 谨慎，标注不确定性 |
| `B/F` | 文化史料与志怪/传说混合（如《搜神记》） | 只作民俗、宗教、叙事氛围，不作事实依据 |
| `C` | 类书、总集、后世汇编 | 只作线索 |
| `M` | 现代研究（版权） | 只引书目/外链 |
| `F` | 小说、演义、影视 | 只作叙事/氛围 |
| `D` | 数据库/工具 | 作入口，回溯原文 |

**冲突处理**：A 级优先；A 级内部冲突时，比较成书年代、史源、作者立场，并在输出中说明分歧。

---

## 6. 游戏数据模型

### 6.1 政权 `faction`

```json
{
  "id": "later-tang",
  "name": "后唐",
  "type": "dynasty",
  "period": "五代",
  "start": 923,
  "end": 937,
  "capital": "洛阳",
  "territory": "中原、河北、关中",
  "founders": ["李存勖"],
  "key_rulers": ["李存勖", "李嗣源"],
  "allies": [],
  "enemies": ["later-liang"],
  "vassals": [],
  "ideology": "唐室继承与沙陀军事集团",
  "military": "沙陀骑兵、藩镇牙兵",
  "economy": "中原农业、河东盐铁",
  "strengths": ["骑兵", "正统号召"],
  "weaknesses": ["财政", "继承不稳"],
  "game_hooks": ["灭梁", "藩镇", "伶宦"],
  "summary": "……",
  "sources": ["JIUWUDAISHI", "XINWUDAISHI"],
  "reliability": "A"
}
```

`type` 常用值：`dynasty, kingdom, empire, warlord, tribal-confederation, garrison, rebel, city-state, foreign`。

### 6.2 人物 `character`

关键字段：`id, name, aliases, courtesy_name, birth, death, birth_place, period, faction_id, roles, tags, traits, relationships, events, quotes, summary, game_use, sources, reliability`。

`relationships[].type` 示例：`君臣、父子、兄弟、夫妻、师徒、盟友、对手、政敌、降附、被杀`。

`events` 必须引用 `data/game/events.json` 中存在的 `id`。

### 6.3 事件 `event`

关键字段：`id, name, year, end_year, period, type, location_id, factions, characters, summary, causes, course, outcome, significance, game_hooks, sources, reliability`。

`type` 枚举（必须使用）：

```text
war, battle, rebellion, coup, succession, reform, treaty, massacre,
migration, disaster, cultural, religious, administrative, diplomatic
```

### 6.4 地点 `location`

关键字段：`id, name, modern_name, province, lat, lon, type, periods, summary, strategic_value, events, sources, reliability`。

`type` 枚举：`capital, city, fortress, pass, region, river, port, religious-site, battlefield`。

### 6.5 术语 `glossary`

`category` 枚举：`institution, military, economy, society, ethnicity, religion, culture, geography, title, law`。

### 6.6 时代 `period`

`data/periods.json` 使用 15 个名称：

```text
东汉末, 三国, 西晋, 东晋, 十六国, 南朝, 北朝, 隋,
初唐, 盛唐, 中唐, 晚唐, 五代, 十国, 宋初统一
```

注意：`data/catalog.json` 使用 `宋初`，游戏数据使用 `宋初统一`；不要混用。

---

## 7. 输出模板

### 7.1 史实问答

```markdown
## 结论
……（1–2 句）

## 史料
1. 《旧五代史》卷……：“……”
   （JIUWUDAISHI，texts/jiuwudaishi/卷…….txt）
2. 《资治通鉴》卷……：“……”
   （ZIZHITONGJIAN，texts/zizhitongjian/卷…….txt）

## 辨析
- A 书与 B 书的差异：……
- 可信度：A；小说/后世演绎不作为依据。

## 游戏化建议
- 机制：……
- 数值/事件钩子：……
```

### 7.2 人物卡

```markdown
### 人物：关羽（guan-yu）
- 时代：东汉末 / 三国
- 阵营：刘备集团 → 蜀汉
- 角色：将领、荆州守将
- 性格：忠义、刚傲、善待卒伍而骄于士大夫
- 关键事件：下邳之战、徐州之战、荆州之战、麦城
- 游戏定位：高统率/高士气，低外交；荆州线核心
- 来源：SANGUOZHI 卷36；ZIZHITONGJIAN 卷……
- 可信度：A
```

### 7.3 事件卡

```markdown
### 事件：高平之战（gaoping）
- 年份：954
- 类型：battle
- 地点：gaoping（山西高平）
- 阵营：后周 vs 北汉 + 契丹
- 人物：柴荣、刘崇、赵匡胤
- 起因：……
- 经过：……
- 结果：……
- 意义：……
- 游戏钩子：御驾亲征、阵前逆转、禁军整编
- 来源：JIUWUDAISHI、XINWUDAISHI、ZIZHITONGJIAN
```

### 7.4 新增数据

新增或修改游戏数据时：

1. 改 `data/factions|characters|events/*.json` 或 `data/locations.json` 等源文件；
2. 运行 `python scripts/build_game_data.py`；
3. 修复所有 `ERROR`；`WARNING` 至少确认可接受；
4. 运行 `python scripts/validate.py`。

不要直接编辑 `data/game/`（生成产物）。

---

## 8. 常见陷阱

1. **同名政权**：魏（曹魏/冉魏/北魏/东魏/西魏）、晋（西晋/东晋/后晋/李克用晋国）、唐（唐/后唐/南唐/武周）、周（北周/后周/武周）、梁（南朝梁/后梁/西梁）、汉（蜀汉/汉赵/成汉/后汉/南汉/北汉）、燕（前燕/后燕/南燕/北燕/安史燕）。先查 `data/game/disambiguation.json`。
2. **时代词表**：目录用 `宋初`，游戏用 `宋初统一`。
3. **小说污染**：`SANGUOYANYI`、`SUITANGYANYI`、`CANTANGWUDAIYANYI` 等是 `F`，不能作为史实。
4. **现代研究**：`M` 级只有书目，没有正文；不要编造引文。
5. **卷次格式**：有 `卷017下` 这种分上下卷，引用时保留“下”。
6. **地名古今**：用 `data/game/locations.json` 的 `modern_name`，不要把唐代“北京”当成今北京。
7. **数字**：古代兵力、户数常有夸张，引用时注明“史载”。

---

## 9. 常用命令速查

```bash
python scripts/build_index.py                 # 建索引
python scripts/search.py 关键词               # 全文
python scripts/search.py --catalog 关键词     # 目录
python scripts/search.py --game 关键词        # 游戏数据
python scripts/search.py --show SANGUOZHI 36  # 读一卷
python scripts/build_catalog.py               # 重建目录
python scripts/build_game_data.py             # 重建游戏数据
python scripts/validate.py                    # 全库校验
python -m unittest discover -s tests          # 测试
```

---

## 10. 任务边界

- 不提供现代版权书籍正文；只给书目与外链。
- 不把演义情节写成史实；如用户要求“演义风”，明确标注 `F`。
- 不伪造卷次、引文、年份。找不到就写“未检出”，并建议换关键词或书目。
- 涉及民族、宗教、暴力事件时，使用历史语境表述，避免现代化标签。
