# 手机端真实全流程排查与验收交接

日期：2026-10-03。本文记录已确认事实与下一步，不表示端到端已经通过。

## 工作范围

项目：`/Users/wufengyu/Projects/wisteria-suite/apps/emjo`，独立 Git 仓库 `git@github.com:sunny314woo/cat-dog-emjo.git`。先阅读 AGENTS.md、docs/PROJECT_OVERVIEW.md、PET_STICKER_PROMPTS.md 的活动 v0.5、deploy/README.md。只改本项目；English Follow、Outline 和同服务器其他服务只读参考。Python/FastAPI/MySQL/pymysql 原生 SQL，禁止 ORM。

正式页面 https://wisteriasoftware.uk/sticker/ ，API https://api.wisteriasoftware.uk/sticker/api 。服务器 SSH `wisteria`，服务 `emjo.service`，监听 127.0.0.1:8013。代码 `/home/wisteria/emjo/current`，私有配置 `/home/wisteria/emjo/shared/server.env`，venv `/home/wisteria/emjo/venv`。使用独立 emjo_stickers 数据库；不重建、不修改其他项目数据库或密码。

凭据不得打印、提交或发布。doubao/、UI/、.local-data/、.local-backups/ 和生产 env 均不得公开。不要将历史文档中的完成描述当作当前实测证据。

## 已确认的失败链路

1. 手机上传两张照片的任务 91b427c553924a8d8e82572f78f3ca49 已进入真实模式，photo_count=2，风格 soft_kawaii_chibi，最终 FAILED，无模型输出。上传不是被猫咪示例照片替代。风格卡片的小猫是固定画风样例，不是用户照片生成结果。
2. 最初配置提取错误：用 UUID 正则截取了凭据中间部分。授权参考文件 `doubao/豆包apikey.txt` 中完整凭据是末尾完整 token，长度46；不能只取36字符 UUID，也不能复制遮罩星号或空剪贴板。密钥不必因此重新创建。
3. 私有配置文件已保存完整密钥。运行进程环境与文件对比结果：运行密钥长度36，文件长度46，两者不一致；运行模型 `doubao-seedream-5-0-lite-260128`，文件模型 `doubao-seedream-5-0-260128`。因此正在服务手机请求的进程尚未加载新配置。这是继续出现认证失败的明确原因。
4. 完整密钥独立请求已经不再返回原先401，但两个模型名的尝试仍出现404 `InvalidEndpointOrModel.NotFound`，含义是模型/接入点不存在或无访问权限，具体原因尚未分清。不能断言删除 lite 即修复。
5. GET /models 返回200，列出 `doubao-seedream-5-0-260128`，状态 Retiring；这不证明该模型可推理。控制台显示 Seedream 5.0-lite 已开通、免费额度50/50；这也不能代替实际 API 验证。在线推理两类接入点当时均暂无数据。不要未经核对就创建语言模型接入点用于生图。
6. 正确基础地址当前为 https://ark.cn-beijing.volces.com/api/v3 ，生图 POST /images/generations。查官方文档核对具体模型标识、权限、退役规则和图生图请求合同；不要猜测。

## 第一优先级：让配置和运行进程一致

先只读检查 systemd 的 WorkingDirectory、ExecStart、EnvironmentFile 及 MainPID。私有读取配置和 /proc/PID/environ，只输出字段名、模型名、密钥长度及是否相同，绝不输出密钥。

若需要重启且免密 sudo 被拒绝，让用户在自己已登录的服务器终端执行：

```sh
sudo systemctl restart emjo.service
sudo systemctl is-active emjo.service
curl --fail --silent http://127.0.0.1:8013/sticker/api/catalog
```

用户自行输入 sudo 密码，不发送密码。只重启 emjo，不重启其他服务。重启后再次核对实际进程环境，并检查公网 catalog、CORS 和安全脱敏日志。不能仅凭文件已上传判断修复完成。

## 第二优先级：真实生图根因验证

使用完整密钥核对官方模型权限和确切 ID；不擅自切换 Flash/Pro 或增加成本。当前目标成本按用户核定的每次生图¥0.22，模型切换需先核对计费和用户选择。接口错误响应应脱敏保留 status、error.code、request id，不记录密钥、base64、原照片或验证码。

按当前 AGENTS 合同：1–3张同一指定主体参考照、固定所选风格、九项动作，一次九宫格；不生成个性化四风格图，不逐张补画，不开放自由 Prompt。先用授权测试照片做一次最小实际调用，成功后再测试手机完整流程；不要反复盲试付费调用。

PNG 格式不等于透明背景。成功后核查实际 alpha、九个主体是否完整分离、尾巴/耳朵是否跨格；当前本地轮廓分离和排布不调用额外大模型。非透明或主体黏连不能伪装成成功交付。可选 rembg 尚未安装验收；不得宣称模型支持原生透明或自动新增付费抠图服务。

## 手机端全流程验收清单

用户说“无法通过验证”可能指生成，也可能指邮件验证码；先明确出错步骤，分别追踪，不能混为一谈。

- 手机真实上传1张和2张照片；原照片确实进入请求；画风卡片明确为样例。生成等待、错误提示、失败权益退回可理解，不显示假成功。
- 真实母图产生九张不同动作，同一主体；完整尾巴、耳朵和身体，切图无邻格残片。单张交付512×512透明PNG。文案由程序叠加，不使“冲鸭”变成鸭子。
- 翻牌预览有背景和烘焙水印。首次免费任选两张，领取后锁定；免费正式单图去背景去水印，其他七张不可绕过权限下载。
- 邮件验证码：真实发送、收件、登录、验证码过期/错误提示；不在日志输出验证码。邮箱规范化唯一，换设备登录仍能看到账户权益。
- 购买前创建真实订单、打开 Paddle checkout，核对实际币种和金额。实际支付由用户操作，不能擅自完成扣款。付款后以服务端签名回调和交易核对确认，不靠前端回调直接发权益。
- 同一套解锁下载九张单图、ZIP、发送邮件；验证实际收件及附件。不能用静态演示文件冒充生成交付。
- 购买1/3/5次 Pack，账户记录累计、已用、生成中、剩余。任务排队预留，成功计已用，失败退回；换设备仍一致；重复支付通知不重复入账。首次套装解锁与后续 Pack 区分。
- WhatsApp分享入口、手机系统文件分享及微信/iMessage可用路径实测；不把普通网页链接称作已成功发送透明贴纸。平台能力限制明确呈现。
- 图片默认24小时到期，Pack余额独立保存；前100份校准案例只有明确同意才保留，当前默认关闭，不私自留用户照片。

## 支付已配置信息（仍未真实成交验收）

Paddle live 产品 pro_01m3m67ms9dxkxckmfvagztmej。价格：
- pri_01m3m6d7yd5hjn5wz071wkwcsy：1套，6.99。
- pri_01m409brwwtwxs98m21yss9kyn：3套，19.99。
- pri_01m409ec0s9f8v4edxg90hhbkq：5套，29.99。

中国地区 CNY，其余 USD；全局自动换币关闭。以 Paddle 实际配置为准，不能修改影响其他产品的全局设置。

专用通知 ntfset_01m40ann8kkrc7s4k8bq9yb871，地址 https://api.wisteriasoftware.uk/sticker/api/webhooks/paddle ，事件 transaction.completed、adjustment.updated。此前界面保存为 Active，无签名请求返回401。私有 Secret 已填写；不输出。现有 API key 为只读，交易 GET 曾返回200；checkout 使用 Paddle.js items + customData，不要求交易写权限。

账号、权益和失败退款逻辑已有代码及自动化测试，但不是生产真实支付/邮件验收。最近代码增加 /me 的 pack_total、pack_used、pack_pending、pack_balance，服务未重启也可能使这些新字段未生效。

## 发布与验收边界

开始先 git status、git fetch origin，保留本地改动。当前项目最近提交 cfb601b；官网最近已知提交 02bfc10。官网源码在外层 apps/website/landing/wisteriasoftware.uk，既有发布通过独立工作树 /tmp/wisteria-sticker-release，只同步 sticker 前端目录；不要动其他项目的脏文件。修改后先本地验证，再按既有 GitHub/Cloudflare Pages 流程发布，检查正式 URL，后端上传后必须确认进程加载实际版本。

自动化15项回归曾通过，使用模拟/本地测试，不能替代真实 Ark、Paddle、Resend 和手机验收。最终报告每一项“已通过／失败／未测试”及证据；只有真实生成、支付确认、权益持久化、透明单图下载和实际邮件收件全部通过，才能称为端到端接通。

## 2026-10-03 本轮复核（仍未通过端到端验收）

- 已执行 `git fetch origin`；保留工作区既有文档修改，未 pull、提交或推送。
- systemd 复核：服务 active，MainPID=3833634，工作目录、EnvironmentFile 和 8013 监听启动参数均指向本项目。私有比对再次确认运行密钥长度36、文件长度46；运行模型带 lite、文件模型不带 lite；模式均为 live，基础地址和 2K 配置一致。未打印凭据。
- 尝试 `sudo -n systemctl restart emjo.service` 返回 `sudo: a password is required`，本轮没有完成重启。已请用户自行在服务器终端执行重启与 is-active 命令。
- 使用文件中的完整密钥执行只读 GET /models，返回200；`doubao-seedream-5-0-260128` 的 status 为 Retiring。此结果不证明拥有实际推理权限。
- 公网 GET /sticker/api/catalog 返回200，Origin 为 https://wisteriasoftware.uk 时，Access-Control-Allow-Origin 精确返回同一域名。此检查不代替手机流程测试。
- [官方模型说明](https://docs.volcengine.com/docs/ark/seedream-4-0-5-0?lang=zh)同时列出 `doubao-seedream-5-0-260128` 与 `doubao-seedream-5-0-lite-260128`，因此不能将去掉 lite 本身视为404修复。
- [官方下线公告](https://docs.volcengine.com/docs/ark/model-deprecation-notice?lang=zh)第十批列出5.0 lite：2026-09-24 10:00（UTC+8）停止新购，2026-11-24 14:00（UTC+8）计划下线。截至本轮日期尚未到下线日；账户是否因停止新购或权限限制无法调用仍待核实，不认定为已找到404唯一根因。
- [官方错误码说明](https://docs.volcengine.com/docs/ark/error-codes?lang=zh&redirect=1)将 InvalidEndpointOrModel.NotFound 定义为模型/接入点不存在或无权访问；不能仅从该错误区分两者。
- 本轮打开方舟控制台时未登录，账户权限核查待用户登录后继续。未更改模型、权限或计费设置，没有发起生图、发送邮件或付款请求。
- 真实生成、透明切图、两张免费领取、验证码登录、支付回调与权益持久化、下载分享、邮件交付：本轮全部未测试；交接中既有生成失败仍未解决。

### 用户重启后的复核与模型建议

- 用户执行重启并返回 active 后，再次 SSH 私有比对：MainPID=3837885，运行密钥长度46，与文件完全相同；模型 `doubao-seedream-5-0-260128`、尺寸2K、live模式均一致。旧配置未加载问题已排除；不代表模型404已修复。
- 依据[官方价格](https://docs.volcengine.com/docs/ark/model-pricing?lang=zh)与[模型说明](https://docs.volcengine.com/docs/ark/seedream-4-0-5-0?lang=zh)，推荐下一步由用户开通 Seedream 5.0 Flash，ID `doubao-seedream-5-0-flash-260915`：参考图输入免费，输出每张0.12元；当前一次生成一张九宫格母图，因此仅模型生图标价成本为0.12元/套，未包含其他成本及重试。Pro输出大于261万像素时0.60元，额外参考图从第2张起每张0.02元。
- 推荐尚未成为生产配置变更，没有切换模型或新增生图调用。Flash单图输出符合九宫格母图方案，但主体一致性、九格完整度和透明交付仍待真实验收。
- [官方API](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh&redirect=1)说明Flash/Pro不支持配置 sequential_image_generation；切换前需调整当前适配器。透明模式仅支持单张带透明通道的输入图片，不可把普通JPEG或多张原照直接视为已支持透明输出。

### Flash 配置已准备，等待再次重启与真实照片验证

- 用户确认控制台已开通Flash，并授权完成API设置。沿用现有完整API Key；没有创建新密钥。
- `server/providers.py` 移除Flash不支持的 `sequential_image_generation` 参数。旧Lite默认也为单图；保留仅接受单张母图的响应校验。
- 新增适配器测试，确认两张原始参考图片均进入请求，Flash请求不带组图参数，且多张返回不会被作为成功母图接受。全套17项自动化测试通过，均不证明真实生图接通。
- 上传前核对远端旧适配器与本地HEAD的SHA-256一致，然后仅上传本项目适配器。服务器私有配置改为 `doubao-seedream-5-0-flash-260915`，保留2K和46字符密钥，将模型成本配置更新为0.12元；未更改其他服务。
- 再次尝试免密重启的SSH调用未返回，已中止本地等待；另一个SSH检查确认服务仍为active/running且PID仍是3837885，尚未确认新配置生效。此前已证实sudo需要用户密码，待用户自行重启后检查进程配置。
- 先前失败任务的目录中已没有可复用原照片。未用示例替代，也未新增模型调用。需要用户重新上传原照片，再进行一次真实生成验收。

### Flash 手机失败与方案 A 确认

- 最新手机任务 `21515685ff0f4ca6b367d0d38cad84b7`：photo_count=1，style=soft_kawaii_chibi，FAILED，failure_code=image_http_429，未保存provider-output.png。失败发生于模型HTTP调用，尚未进入切图。历史代码未保存细分错误码，不能仅凭429断定是限流、额度耗尽还是安心体验限额。
- 进程PID=3838573，运行模型与文件均为Flash，密钥匹配。不能再把这次失败归因于未重启或旧模型。
- 当前背景移除配置为空，实际不会启用rembg；默认只接受已有透明输出。即使429解除，透明处理仍是独立的待验收阻断项。
- 已在本地补充上游HTTP状态、错误码、request ID白名单式脱敏记录，并区分generation/processing阶段。绝不记录完整上游消息、响应体、原图、密钥或验证码；不加入自动生图重试。
- 用户明确方案A：原照生成四风格，再以原照和选中单张风格生成九宫格，覆盖旧固定样例方案。详细合同记录在AGENTS.md与增量决策文档。四种风格的真实质量仍均未验收；当前任务只试过软萌Q版且在生图HTTP阶段失败。
- 本轮打开控制台仍显示未登录，已请用户登录后只读核查Flash额度、限流与安心体验设置。未充值、未关闭消费限额、未调用新增文本模型或生图。

### 2026-10-04 两阶段部署复核

- 方案 A 代码已实现：一张四风格母图裁成四份，第二次请求只携带原照片和选定的一张风格参考；增加风格预览到期、放弃、失败退还预留权益与重复请求保护。27 项 pytest 回归通过，属于模拟与程序逻辑测试，不是真实模型验收。
- 服务器已安装 rembg[cpu] 2.0.67 和 u2netp，使用低优先级、单线程、限时独立进程抠图。2K 白底测试素材实际经过服务器抠图后，输出九张 512×512 透明 PNG；不是新调用模型产生的图片。高置信主体黏连仍拒绝交付。
- 新代码已部署到 /home/wisteria/emjo/current；备份 /home/wisteria/emjo/backups/before-two-stage-20261003-132649。用户把重启和状态查询误粘在一行，虽然出现其他服务名错误，但 emjo 实际已重启成功：PID 3842850，active/running，catalog 返回 personalized_styles_v1。
- 私有核对运行配置与文件一致：live、doubao-seedream-5-0-flash-260915、rembg、EMJO_REQUIRE_STYLE_PREVIEW=true、流程成本0.24元，API key匹配。未修改其他服务。
- 用户已开启 Chrome 扩展文件访问，浏览器上传恢复。本地模拟流程已走通上传、四风格选择、九宫格和免费领取两张；页面明确标注样例，不能当成真实 AI 成功。
- 官网贴纸目录三个前端文件已提交至官网源仓库 main：a06fafd；同步任务37171231739成功，正式域名 app.js 和 styles.css 与本地新版 SHA-256 完全一致。未发布凭据、后端、doubao、UI 或测试照片目录。
- 火山控制台安心体验仍显示已开启；此前 Flash 无免费额度且暂停。用户授权一次两阶段真实测试约0.24元，但本轮尚未发起，授权未消耗。等待用户自行关闭全局安心体验；不能自动关闭或循环付费重试。
- 真实四风格质量、真实九宫格及透明质量、生产免费领取、验证码收件、实际付款和回调、生产下载分享、邮件交付仍未完成验收。

### 2026-10-04 已授权的一次真实两阶段测试

- 用户关闭安心体验后，控制台复核：开启标记消失，Flash 状态为已开通，无服务暂停标记。沿用 Flash，未切换 Pro 或新增文本模型。
- 用项目 assets/cat-photo.png 作为独立技术测试输入，生产 API 新建任务 8875b4256dc247e195f03d301c311bae。这是项目测试素材，不是用户手机上传照片；没有替换用户已有任务的原图。
- 两次真实调用顺序完成：PREVIEW_QUEUED → PREVIEW_GENERATING → STYLE_READY；选择 soft_kawaii_chibi 后 QUEUED → GENERATING → PROCESSING → READY。未重试生成，模型标价费用约0.24元，已使用此前授权的一次测试。
- 四张风格预览已实际下载并目视检查；描边和水彩有所区别，但整体差异偏小，不能称为四种风格质量全部验收通过。实际九宫格具有九个不同表情，主体分离后完整排版；感谢动作的小花存在抠图丢失，配饰保留质量仍需改进。
- 生产免费领取第1、2张通过，两张下载为512×512 RGBA PNG，alpha范围0–255。领取前以及领取后，未选第3张正式PNG均返回403；生成的分享链接匿名下载返回200。完整九张技术检查文件留在私有测试目录，没有开放锁定贴纸的网页权限。
- 私有测试产物 /home/wisteria/emjo/shared/live-check-20261004 和本地 .local-backups/，不提交、不公开。生产任务仍按默认24小时到期清理。
- 已通过：本次测试素材的真实两阶段生图、九张输出、透明PNG格式、生产免费领取两张、下载权限及单图分享链接下载。待验收：四种风格区分度、细小配饰保留、用户手机原照片结果、手机系统文件分享、验证码真实收件、真实支付/回调与完整解锁、邮件交付收件。完整端到端尚未通过。
