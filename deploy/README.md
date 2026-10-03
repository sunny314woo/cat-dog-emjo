# 独立服务器部署（待填写配置）

本服务独立使用 `/home/wisteria/emjo`、8013 端口和独立 MySQL 数据库/用户。不得复用或修改 Outline、语音服务数据库、环境文件或 service。

## 服务器准备状态

代码与空配置上传至本项目的独立目录；未启用公网路由、未启动真实支付/生图。SSH 用户没有免密 sudo，安装 systemd 与修改 Nginx 需要服务器管理员操作。现有服务不重启。

## 配置与启用

1. 编辑 `/home/wisteria/emjo/shared/server.env`，填写 `.env.example` 中的火山模型、尺寸、API key、Paddle API/client token、webhook secret、四个价格 ID、Resend 和发件地址。价格 ID 不复用旧商品。
2. 设置 `EMJO_MODE=live`、`EMJO_PUBLIC_URL=https://wisteriasoftware.uk/pet-stickers`、`EMJO_DATA_DIR=/home/wisteria/emjo/shared/data`、独立会话密钥；使用新的 MySQL 数据库/用户并执行 `server/schema.sql`。不要在其他业务库执行。
3. 免费日预算 `EMJO_DAILY_FREE_BUDGET_CNY` 由运营填写；`EMJO_COST_PER_GENERATION_CNY` 填写实际生成流程成本。当前实现一次九宫格调用，个性化四风格预览 + 九宫格的两次调用流程尚未完成，不应提前按已接通宣传。
4. 新建独立 venv，安装 `server/requirements.txt`。安装 `deploy/emjo.service` 至 systemd；启动前校验会拒绝空配置。
5. 核对官网实际域名源站，再把 `deploy/nginx-location.conf` 加入对应 HTTPS server 块。检查 `nginx -t` 后仅 reload nginx。禁止覆盖整个现有配置。若官网由其他平台托管，需要在该平台配置 `/pet-stickers/` 路径代理。
6. Paddle 通知目标：`https://wisteriasoftware.uk/pet-stickers/api/webhooks/paddle`；checkout 默认链接使用 `https://wisteriasoftware.uk/pet-stickers/checkout`。先沙箱验证完整支付、重复通知、退款及邮件，再切换 live。

所有配置应为权限 600，data 目录 700。服务仅监听 loopback，不开放 8013 公网端口。删除该独立 service 和本项目路径即可回滚；不触碰其他服务。

## 本次可执行安装入口

本地填写：项目根目录 `.env.production`（已忽略，不提交）。服务器填写：`/home/wisteria/emjo/shared/server.env`。两者二选一，避免覆盖另一处已填好的配置。

本地写好后上传：

```bash
scp /Users/wufengyu/Projects/wisteria-suite/apps/emjo/.env.production wisteria:/home/wisteria/emjo/shared/server.env
```

在服务器终端运行（sudo 密码自行输入）：

```bash
sudo bash /home/wisteria/emjo/current/deploy/install.sh
```

脚本只安装本项目 venv、建立 `emjo_stickers` 独立库和用户、安装/启动 `emjo.service`。缺少 API 配置会停止并列出变量名，不输出密钥。会自动创建本项目会话密钥和数据库密码。服务器 root MySQL 需支持本机 socket 登录，失败即停止，不修改其他业务库。

首套解锁和单 Pack 暂时都使用已有 `pri_01m3m6d7yd5hjn5wz071wkwcsy`，结账金额以 Paddle 当前实际价格为准；三/五 Pack 未配置则不开放。上线前可替换独立价格。官网路径代理仍需核对官网源站后配置，此安装脚本不会盲目改动现有 Nginx。

## 已回填的配置

从 Outline 本地/当前服务器配置读取并私有回填 Resend API Key、发件地址、Paddle API Key；从官网支付代码读取 Paddle Client Token；从豆包 HTML 读取火山模型 `doubao-seedream-5-0-lite-260128`、接口与 `2K` 尺寸。会话签名密钥已随机生成，无需用户手写。免费生成每日总预算暂设 10 元，可修改 `EMJO_DAILY_FREE_BUDGET_CNY`。没有发送测试邮件或调用付费生图。

当前仍缺火山 API Key（HTML 默认值为空，设置保存于浏览器 `meme_settings`）以及贴纸专用 Paddle Webhook Secret（Outline 的 secret 属于另一通知端点，不直接复用）。当前 Paddle API 查询 notification-settings 返回 403，未能自动读取专用端点配置。

后续配置补充：已从本项目 `doubao/豆包apikey.txt` 私有读取并回填火山 API Key；该原始文件及目录不提交、不发布。3 Pack 价格为 `pri_01m409brwwtwxs98m21yss9kyn`，5 Pack 价格为 `pri_01m409ec0s9f8v4edxg90hhbkq`，已同步本地与服务器私有配置。前文“火山 API Key 缺失”与“三/五 Pack 未配置”状态已被本条更新替代。真实价格产品归属及支付/生图仍需联调；专用 Webhook Secret 尚未配置。

## 最新预算、部署与价格状态

全站每日免费预算已取消：`EMJO_DAILY_FREE_BUDGET_CNY` 留空即不限全站每日金额，不再阻断免费制作。当前固定风格样例 + 一次九宫格调用，内部成本暂记 0.22 元；两次调用流程才是 0.44。用户不需要填写数据库密码，安装脚本自动生成，只建立 `emjo_stickers` 独立库和用户。Webhook 尚未完成时允许部署生图服务，但禁止结账，防止扣款后无法解锁。

最新价格目标：首次解锁 6.99，3 份 19.99，5 份 29.99；中国地区 CNY，其他地区 USD。以 Paddle 实际价格为准，当前读取价格端点返回 403，地区价格尚未核实，旧价格 ID 可能仍是旧金额。主域名官网路由仍需核对源站后启用。安装脚本只安装本项目依赖及缺失的中文字体，不修改其他业务服务。


## 2026-10-03 正式发布路径
官网产品页：`https://wisteriasoftware.uk/sticker/`。静态文件从官网源码发布，不包含服务器代码、配置、doubao 或 UI。
API：`https://api.wisteriasoftware.uk/sticker/api`，独立服务 8013。通过 `sudo /home/wisteria/emjo/venv/bin/python /home/wisteria/emjo/current/deploy/enable_api_route.py` 启用精确路由并重启本服务。脚本只插入 Sticker location，先备份并验证 Nginx。
Paddle 通知地址改为 API 上的 `/sticker/api/webhooks/paddle`。网页使用 Paddle.js items/customData 建立结账；服务器验证签名并通过只读 API 复核 transaction.completed，不需要交易写权限。
私有配置增加 `EMJO_ASSET_URL=https://api.wisteriasoftware.uk/sticker`；`EMJO_PUBLIC_URL=https://wisteriasoftware.uk/sticker`。
