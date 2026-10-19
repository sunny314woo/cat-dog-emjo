# 自助表情包生成器 · My Pet Stickers

用 1–3 张同一人物或宠物的原照片制作一套九张表情。先生成个性化四风格预览，再按选中的单一画风生成九宫格，经过透明处理、完整主体分离、排版和文案叠加后交付。

- 正式 H5：[wisteriasoftware.uk/sticker/](https://wisteriasoftware.uk/sticker/)
- 正式 API：`https://api.wisteriasoftware.uk/sticker/api`
- 独立仓库：[sunny314woo/cat-dog-emjo](https://github.com/sunny314woo/cat-dog-emjo)，主分支为 `main`。Git 操作在本目录执行，与外层 Wisteria Suite 仓库分别管理。

## 当前状态（2026-10-19）

本轮作品与订单关系修复已通过测试，后台已备份上传；新增后台仍待本轮重启，官网前端尚待发布授权。此前 v0.9 重启已成功。部署状态、已补齐的旧 ZIP 与待确认交付见 [本轮交接](docs/ai-handoff/order-work-fulfillment-2026-10-19.md)。

| 项目 | 状态与验收范围 |
| --- | --- |
| 邮箱与免费体验 | 正式制作前先验证邮箱；同一规范化邮箱一次免费体验，任选两张正式贴纸下载、分享。 |
| 两阶段制作 | 原照生成一张四风格母图；选中后，由原照加一张风格参考生成九宫格，共两次生图。 |
| 原套解锁 | 付款解锁已有同一套九张，不重复生图、不额外增加新制作余额；合法全额优惠完成订单正常交付。 |
| 套数额度 | 可购买 1／3／5 套额度，每套九张；每份已有作品可使用 1 套额度解锁，也可新制作 1 套。绑定作品购买时先解锁该作品，其余额度保留；首次优惠资格单独判断。未配置支付或未取得实时报价的套餐隐藏。 |
| 设置与分享 | 作品显示缩略图、编号、独立解锁状态及来源订单；订单显示实际结算金额、已购／已用／剩余套数和关联作品。零余额不影响已解锁作品下载；分享底色用于检查透明区域。 |
| 交付 | 同一套九张的多尺寸 PNG、静态 GIF、WebP、整套 ZIP 与邮件交付。 |
| 提示词 | 当前执行版本 `v0.9-human-silhouette`，强化人物辨识、动作与视角差异、双眼协调、衣物完整轮廓。部署不等于实图质量验收。 |
| 素材保留 | 当前保留未付款生成作品，`EMJO_DEBUG_RETAIN_ASSETS=true`；约30天清理仅为后续计划，尚未启用。上传原照仍按隐私规则处理。 |
| 已知质量限制 | 历史付费九张已完成一次保留全部 RGB 的 alpha 返修；通用自动抠图、Mac 微信普通 PNG 消息白底显示及新版动作实图仍需验收。 |

2026-10-19 17:04:39（北京时间）后台已成功重启；随后通过 loopback 与公网 API 核实，常驻服务已加载 `v0.9-human-silhouette`、邮箱前置与素材保留配置。代码、网站发布、服务器加载和返修证据见 [最新交接](docs/ai-handoff/quality-v09-matting-repair-2026-10-19.md)。

3／5 套的支付配置与公开实时报价已核对，报价成功不等于本轮对两种套餐重新做过真实扣款验收。金额、币种与税费以 Paddle 结账页为准。

## 产品流程与规则

1. 验证邮箱，上传 1–3 张同一主体原照片；合照须指定一个主体，可按需要裁剪。
2. 一次生成 2×2 四风格预览，程序裁成四张供选择。十三种候选风格全部保留，当前界面展示其中四种。
3. 以原照片和选中的单张风格参考生成一张九宫格；不同时注入四种画风，不开放自由 Prompt，不逐张 AI 补画。
4. 本地处理透明背景、分离完整主体、缩放排版，按配字选项叠加固定文案，提供保护预览。
5. 首次体验可任选两张，确认后锁定选择；优惠付款或使用 1 套已有额度后解锁同一套全部九张并排队邮件交付。首套优惠限一次，其他作品仍可普通单套购买或使用额度解锁。
6. 后续新制作使用 1 套额度，技术失败退回。账户可多次购买 1／3／5 套；每笔额度订单记录已用、预留、剩余及使用去向。同邮箱换设备、重新登录或清除浏览器记录不会重置免费资格。

需求基线为 [V2.3 整理稿](docs/PROJECT_OVERVIEW.md)，冲突处依次采用后续明确决定：[两阶段制作](docs/product/IMPLEMENTATION_2026-10-03.md)、[邮箱前置与保留策略](docs/product/DECISIONS_2026-10-18.md)、[透明与表现力要求](docs/product/QUALITY_REVISION_2026-10-18.md)。历史文档中匿名生成、固定样例代替个性化预览、未付款24小时删除等旧规则不作为当前流程。

主要单位统一用“套”，1 套＝9 张不同表情；多格式与尺寸不重复计套数。当前一次制作实际为 1 套，尚无可直接交付的 27 种不同表情库。多套商品表示可分次使用的制作额度，不能理解为付款后立即出现 27／45 张新图片。详细关系见 [作品、订单与套数](docs/product/ORDER_WORKS_2026-10-19.md)。

## 本地运行

需要 Python 3.10 或更高版本。以下命令在项目根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
EMJO_DATA_DIR=.local-data EMJO_PUBLIC_URL=http://127.0.0.1:4173/sticker .venv/bin/python tools/run_local.py
```

打开 [http://127.0.0.1:4173/sticker/](http://127.0.0.1:4173/sticker/)。本地示例验证码为 `123456`。

`tools/run_local.py` 强制使用 `demo`：固定样例用于验证交互，不根据新上传照片调用真实模型，不收款、不发送邮件。数据写入私有 `.local-data/`。完整流程依赖 FastAPI 接口，不能只运行 `http.server` 或直接打开 HTML。

样例导出也需要中文字体。macOS 可使用系统 PingFang／STHeiti，Linux 可安装 Noto CJK；其他环境通过 `EMJO_FONT_PATH` 指向可用中文字体文件。缺少字体时导出会报错，不能用缺字图片交付。

本地示例不需要 MySQL、服务密钥或抠图模型。请勿让本地进程沿用生产数据目录。

## 测试

`pytest` 是开发测试依赖；付款监控使用 Node.js 内置测试，无需安装 npm 包。

```bash
.venv/bin/python -m pip install pytest
EMJO_MODE=demo .venv/bin/python -m pytest tests -q
node --test tests/test_payment_monitor.cjs
```

最近一轮通过 89 项 Python 测试和 10 项 JavaScript 测试，覆盖两阶段状态、领取权限、付款通知幂等与恢复、指定作品解锁、额度来源与退款、保留策略、透明导出、受控返修和失败恢复。浏览器使用公开样例与真实 demo API 验证两份作品独立解锁、余额3→2及订单关联；不把样例邮件状态当成生产发送成功。

自动测试主要使用示例存储与模拟提供商，不代表真实 MySQL 压测、每种支付套餐实际扣款或真人生成质量已全部验收。

## 技术结构

前端为原生 HTML／CSS／JavaScript；后端为 Python／FastAPI。正式数据使用独立 MySQL 数据库，通过 pymysql 和原生 SQL 访问，不使用 ORM。本地 demo 使用私有 JSON 状态。

| 路径 | 用途 |
| --- | --- |
| `index.html`、`styles.css`、`app.js`、`config.js` | H5 界面、状态交互及公开 API 地址。 |
| `config/catalog.json` | 十三种风格、九项动作语义和商品权益定义。 |
| `server/catalog.py` | 两阶段 Prompt 组装及执行版本。 |
| `server/main.py`、`server/service.py` | API、账户、任务、领取、订单、权益及交付队列。 |
| `server/providers.py` | 火山图片、Paddle 与 Resend 服务端适配。 |
| `server/imaging.py`、`server/slicing.py`、`server/matting*.py` | 透明处理、完整主体分离、多格式导出。 |
| `server/store.py`、`server/schema.sql` | 本地存储与正式 MySQL 原生 SQL。 |
| `deploy/` | 独立服务配置、启动检查、部署和受控资产返修工具。 |
| `tests/`、`tools/` | 回归测试、本地运行和目录同步工具。 |
| `docs/product/`、`docs/ai-handoff/` | 产品决定、验收边界与部署交接。 |

当前低并发 MVP 使用短数据库互斥事务处理账户权益与通知；外部服务请求和图片处理在事务外执行。扩容前需要验证数据库与工作队列并发，不直接增加多个 worker。

## 正式配置与部署

部署步骤见 [deploy/README.md](deploy/README.md)，以顶部最新状态和交接为准；下方保留的旧路径及单阶段说明属于安装历史。现有服务为独立 `emjo.service`，使用独立数据库、数据目录和 loopback 8013 端口；不修改或重启同台账号、语音、Outline 等其他服务。旧 `pet.wisteriasoftware.uk` 是历史站点。

配置以 [.env.example](.env.example) 为参数参考，真实值由服务进程环境注入。程序不自动读取项目 `.env`；正式 systemd 使用其 `EnvironmentFile`，手动启动须显式加载所需环境。

| 配置组 | 关键变量 |
| --- | --- |
| 运行与地址 | `EMJO_MODE`、`EMJO_PUBLIC_URL`、`EMJO_ASSET_URL`、`EMJO_DATA_DIR`、`EMJO_SESSION_SIGNING_SECRET` |
| 独立数据库 | `EMJO_MYSQL_HOST`、`EMJO_MYSQL_PORT`、`EMJO_MYSQL_DATABASE`、`EMJO_MYSQL_USER`、`EMJO_MYSQL_PASSWORD` |
| 生图 | `VOLCENGINE_API_KEY`、`VOLCENGINE_BASE_URL`、`VOLCENGINE_MODEL_ID`、`VOLCENGINE_FINAL_SIZE`、`EMJO_REQUIRE_STYLE_PREVIEW` |
| 支付 | `PADDLE_ENVIRONMENT`、`PADDLE_CLIENT_TOKEN`、`PADDLE_API_KEY`、`PADDLE_PRODUCT_ID`、各商品 `PADDLE_PRICE_*_ID`、`PADDLE_WEBHOOK_SECRET` |
| 邮件 | `RESEND_API_KEY`、`MAIL_FROM`；发件域名须在 Resend 验证。 |
| 抠图、配字与保留 | `EMJO_BACKGROUND_REMOVAL_MODE`、`U2NET_HOME`、`EMJO_FONT_PATH`、`EMJO_DEBUG_RETAIN_ASSETS` |

正式 Paddle 环境值为 `live`。结账使用 Paddle.js；签名通知入队后，后端通过交易读取接口复核完成状态、订单、价格、商品、数量和优惠，确认后才授予权益与交付。不能仅凭前端成功事件解锁。

线上目前使用本地 rembg／u2netp，不宣称图片模型原生输出透明。启用抠图时另安装 `server/requirements-matting.txt` 并预先配置本地模型；不要让请求临时下载未验收的大模型。正式资源与质量限制见最新交接。

官网只发布前端允许清单和公开 `assets/`，后端代码、环境文件、上传原照与订单资产不进入静态站点。独立仓库推送与官网前端发布是两条流程，`git push` 不会自动完成服务器服务重启。

更新现有后台后，在服务器终端逐行执行，每行按一次回车：

```bash
sudo systemctl restart emjo.service
sudo systemctl is-active emjo.service
```

两条命令之间不要加中文顿号。`active` 只表示服务运行，还应核对正式 `/sticker/api/catalog` 的 `pack_prompt_version`、`generation_requires_email` 和 `debug_retain_assets`，确认实际加载版本。

## 文件交付与透明验收

每套 ZIP 包含47项，同一套九张导出为：

| ZIP 内路径 | 格式与尺寸 |
| --- | --- |
| 根目录 `sticker-1.png` 至 `sticker-9.png` | 512×512 RGBA PNG 母版，保留半透明边缘。 |
| `PNG-256/` | 九张256×256 PNG。 |
| `PNG-240/` | 九张240×240 PNG。 |
| `GIF-240/` | 九张240×240静态透明GIF，二值透明，不是动画。 |
| `WebP-512/` | 九张512×512 WebP。 |
| `grid.png`、`README.txt` | 整套九宫格及使用说明。 |

分享预览的蓝／深色底只用于检查，底色不写进文件。存在 alpha 通道不能证明衣服、头发或配饰完整；应检查内部不误透明、外部无残纸、主体无截断，并分别验证目标聊天软件的发送效果。

用户在 Mac 微信普通图片消息中看到 PNG 白底，同一文件另存为后仍保留原 alpha；此客户端显示路径尚未解决。GIF 可用不能替代 PNG 用户端验收。

对明确审核过的历史资产，可使用 `deploy/repair_pack_assets.py` 做仅 alpha 变化的返修。工具要求准确审核哈希、尺寸及全部 RGB 像素相同，先完整备份，再重导出并记录素材版本；不生图、不扣制作次数、不发邮件。操作方法与已应用记录见最新交接，不能将本套人工标注规则自动应用于未知图片。

## 隐私与仓库边界

- `doubao/`、`UI/` 是本地实验或设计参考，可能含凭据，整个目录不得提交或发布。
- `.env`、`.env.production`、`.local-data/`、`.local-backups/`、真实用户图、生成素材和模型文件留在私有目录；`.env.example` 只放空值或占位符。
- 生成作品当前暂不删除；后续约30天清理需单独实施并给旧作品过渡窗口，不直接关闭保留开关触发旧过期时间。
- 暂停成品清理不等于无限保存上传原照。原照仍按既有隐私规则删除；重新生成需要原照，不用现有贴纸或固定样例替代。

## 文档入口

- [本轮作品、订单与交付修复交接](docs/ai-handoff/order-work-fulfillment-2026-10-19.md)
- [最新部署与返修交接](docs/ai-handoff/quality-v09-matting-repair-2026-10-19.md)
- [邮箱、免费体验、全额优惠及保留策略](docs/product/DECISIONS_2026-10-18.md)
- [作品、订单、套数余额与交付关系](docs/product/ORDER_WORKS_2026-10-19.md)
- [透明图片与九格表现力要求](docs/product/QUALITY_REVISION_2026-10-18.md)
- [完整主体分离与排版合同](docs/product/IMAGE_LAYOUT_CONTRACT.md)
- [Prompt v0.5 模块库及执行补充](PET_STICKER_PROMPTS.md)：历史 v0.1 附录不注入活动模板。
- [十三种候选风格研究](docs/research/sticker-styles-2026-10-02.md)
- [独立服务部署说明](deploy/README.md)
