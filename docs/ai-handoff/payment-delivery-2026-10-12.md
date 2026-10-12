# 2026-10-12 支付回调与邮件交付

## 用户决定与价格

最低档改为 USD 10，原 Price ID 不变，区域价格已取消。订单仍传原 Price ID，由 Paddle.js 获取当前报价，金额以结账页为准。没有改 Paddle 价格、币种转换或其他项目设置。当前服务密钥读取交易 HTTP 200、读取价格 HTTP 403，不能用私有 API 证明新的报价。

## 已完成代码

- 签名通知先写入本项目 MySQL 的 payment_notifications，写入成功后返回 200。回调不等待 Paddle 交易 GET，不存完整客户或付款载荷。
- 后台独立处理付款、邮件和生成。付款查询暂时失败按 30 秒起步、最多一小时的间隔继续重试；处理中断的任务在 120 秒租约结束后恢复。商品不匹配进入 REVIEW，不发放权益。
- 原事件与订单幂等保持；完整退款先到达时保存交易退款标记，后到付款通知不重新发放。部分退款保留人工 review。
- 首次解锁在结账与确认时检查原 ZIP 存在；付款确认后解锁同一作品，排队发送九张贴纸，不重复生图。Pack 付款增加制作次数，作品制作成功后进入邮件交付。
- 邮件重试使用持久化的相同下载期限与幂等键，防止内容变化导致 Resend 重试冲突；保存邮件服务返回的 provider_id。最多四次尝试，失败重试间隔沿用五分钟递增。
- 前端保存订单，刷新或重新验证邮箱后继续查询。确认等待延长，显示邮件发送、重试与失败状态；邮件服务接收不等于用户邮箱实际收件。
- /catalog 新增 payment_workflow=durable_notifications_v1，部署后核对进程实际加载。

## 验证与部署边界

本地后端43项回归通过，覆盖签名拦截、持久化、重复通知、失败重试、重启恢复、退款先到达、商品不匹配、邮件相同内容重试、返回邮件 ID，以及生成阻塞时付款/邮件仍运行。前端3项脚本测试通过，覆盖较晚确认、刷新恢复、退出时过期请求被忽略。本地浏览器验证邮箱与账户界面属于 demo，不发送邮件；390像素视口页面宽390、设置弹窗358，无横向溢出，浏览器无报错。

代码部署后需重启独立 emjo.service，核对公网 catalog 的 payment_workflow。sudo 密码由用户在服务器终端输入。未重启前不得称新版后端生效。

本轮发布：独立项目 main 提交 e4e1208 已推送 GitHub；官网源码提交 2183f5a 的同步工作流 38223564019 成功，公网 app.js 与 index.html 字节哈希均与本地一致，缓存版本20261012-payment。服务器四个新文件已逐一校验、备份并原子替换，备份位于 /home/wisteria/emjo/backups/payment-delivery-20261012。sudo -n 重启返回需要密码，最近进程 MainPID=4072151、公网/loopback catalog 无新 payment_workflow，故后端仍待用户重启后核验，不能在此状态开始首笔真实付款验收。

用户执行重启并报告 active 后，本轮只读复核确认新版已加载：2026-10-12 16:43:26（北京时间）启动，MainPID=4097883、ActiveState=active；服务器支付核心文件哈希与发布版本一致。loopback 与公网 catalog 都返回 payment_workflow=durable_notifications_v1、Paddle live、debug_retain_assets=true。重启后的可读日志没有 Background operation failed。数据库仍只有一笔 PENDING，无 payment_notifications、mail 或人工 review；这些结果不等于实际付款/邮件验收通过。服务器 Python urllib 请求公网曾返回403，随后本地 curl 公网请求200并读取到新版字段；尚未用真实 Paddle 请求验证其外部投递。

真实付款、Paddle 实际通知投递、实际邮箱收件仍未验收。原数据库只读检查：一笔 PENDING 订单，无支付确认事件与交付邮件；发件域名已验证。未新增付费生图或代付。

## 下一步真实验收

1. 核对新版进程已加载，贴纸专用通知地址正确且 Active，包含 transaction.completed、adjustment.updated。
2. 已生成作品点解锁，确认结账最低档报价 USD 10（税费以 Paddle 结账页为准）、一次性付款；实际付款由用户完成。
3. 查 Paddle completed 与通知投递 200；本项目订单 PAID、同一作品 unlocked，九张和 ZIP 下载可用。
4. 查邮件记录 SENT 与 provider_id，再由用户确认收件箱/垃圾邮件实际收到附件，ZIP 可解压。付款后网页查询慢时不要重复付款。

尚未改动的限制：取消结账的待支付订单可同商品重试，切换另一商品可能被待支付订单阻挡；REFUND_REQUIRED 只标记人工处理，不自动发起退款。调试保留配置继续按 2026-10-11 规则执行。
