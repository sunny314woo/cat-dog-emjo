# 2026-10-19 作品、订单与三套额度交付

## 产品决定

主要用“套”，1套等于9张不同表情；多格式尺寸不重复计数。现有3/5套商品是可分次使用的额度，并非已生成27/45张不同图片。用户尚未决定扩展为同主体新表情系列；本次不开放不存在的表情库。详见 [作品、订单与套数](../product/ORDER_WORKS_2026-10-19.md)。

## 生产核查

只读核查时间2026-10-19 13:43 UTC：

- 三套订单 `9b56cf0c859247a18105db8ca0b465c8`，PACK_3／PAID，实际结算USD0（合法全额优惠），grant数量3、可用3、已用0；通知DONE。不能说已扣US$19.99。
- 第二作品 `3fe2d5424c3749d1bf3a3178c98904ca`，READY／未解锁／非免费，无grant，无邮件；原照片已删除。
- 原首套 `2e6a16373f0f4bcd954c1dbe67c1f717` 已独立解锁，原邮件SENT；本次不改其九张或权益。
- 四种商品价格配置均存在。前端PACK_1展示不按paid_once过滤；不能仅凭账户付过费断言单套报价被账户隐藏。旧结果页仅提交FIRST，非免费或优惠已用作品因此无正常普通单套解锁路径。

## 修复

- `POST /sticker/api/generations/{jid}/unlock`：本人READY且真实ZIP存在时，可用1套余额解锁；事务幂等，并发/重复不再扣。直接排队既有作品邮件，不生图。
- PACK_1/3/5可绑定generation_id。结算后授予N套，用其中1套解锁指定作品；剩余N−1保留。无目标的历史/纯充值保持原权益，不猜测其对应照片。
- 首套优惠资格保留账户一次；普通购买或余额解锁不受该资格限制。第二笔完成时若作品已被另一笔解锁，本单额度全部保留并明确说明。
- 所有绑定目标均核对归属、READY、有效窗口和ZIP；退款按真正支持权益的来源撤销，不能因仅绑定同一作品而锁掉另一笔有效权益。
- 新`grant_uses`桶使用现有原生SQL文档表，记录历史额度使用，无需DDL迁移。退款后更换来源不会丢失旧订单使用去向。
- 历史/API返回作品对应订单、每单数量/已用/预留/剩余、关联作品、逐作品邮件状态和实际结算金额。额外真实交易进入review，订单明确显示核验异常。
- 前端主要显示套数、作品编号和缩略图。购买时说明目标及扣后余额；账户可反复购买，已解锁同套不重复收费。
- `catalog.order_workflow=work_bound_packs_v1`。旧后台没有该字段时，新前端禁止余额解锁和绑定作品付款，避免发布窗口再次只充值不交付。

## 第二作品旧ZIP补齐（已应用，不扣余额、不发邮件）

发现旧ZIP仅11项：九张PNG、grid、README。以现有九张512母版重新调用`build_delivery_archive`，不重新抠图、不配字、不调用模型；母版和拼图逐字节保留，补出PNG256/240、GIF240、WebP512。

- 旧ZIP SHA256：`9f321f16baa6bf72e5e1a5ee0ee67e7c6a60eec56d91634f390c3fe2875c0780`。
- 新ZIP SHA256：`52b96cf4c24be46402795c89bdb332c3f5b79a3448d8512a6d999e1ab36ba9b7`。
- 已核对47项、45张图片的尺寸及透明数据；原九张PNG和grid哈希不变。
- 原ZIP完整备份：`/home/wisteria/emjo/shared/data/asset-repairs/order-work-20261019-3fe2d5424c3749d1bf3a3178c98904ca/stickers-original.zip`，私有receipt及`delivery_repairs`记录；job.delivery_revision=1。
- 仅补齐文件打包，不代表人物、衣服语义抠图或微信PNG显示已通过。

## 部署与待确认

后台三文件server/main.py、server/service.py、config/catalog.json已核验旧哈希、备份、上传并编译检查。备份目录：`/home/wisteria/emjo/backups/order-work-20261019-135908`。

本轮新增后台尚未重启；sudo非交互返回需要密码。此前17:04的v0.9重启确已成功，此处是其后的新订单修复。用户完成以下两行后，应核验loopback/公网catalog的order_workflow为work_bound_packs_v1，并记录进程时间：

```bash
sudo systemctl restart emjo.service
sudo systemctl is-active emjo.service
```

官网前端已于2026-10-20发布，具体仅sticker/app.js、index.html、styles.css三文件。此前自动审批因项目规则限定“只修改本项目文件”拒绝外层仓库写入；用户随后明确要求“帮我发布官网”，本轮据此获准完成限定范围发布。

上次正式核查余额为3套、第二作品未解锁、没有新邮件。本轮官网发布没有变更余额或发送邮件。只读预演已确认：若用户同意，使用上述订单1套解锁第二作品后剩2套，将现有完整ZIP寄至原绑定邮箱。不得在用户确认前扣除或发送。预演脚本、服务器staging与所有私有receipt只在私有目录，不提交。

### 2026-10-20 官网发布核验

- 源站提交：`aa939763b2cd6deebaba5e2d7cabc39081986d4a`，基于已核对的`5f49e67372cb7a3504b59342b7963fed48ed88ea`；差异仅上述三文件，非强制快进更新main。
- Sync website repo：`39399606368`，success；Check website i18n：`39399606391`，success。
- 正式HTML SHA256：`3bb8a16e3e5586eca10f0d5d65a2f525cc7df60f1041dd202faa3298e2080eb3`。
- 正式app.js SHA256：`4ff470b877d9431c039805f4a2cb991befcacbb22d7bcba0fba4268954036230`。
- 正式styles.css SHA256：`2d78886709b3bce28c62a932d09ac12c19382495d7f4d846e4f33ab333c65c93`。
- HTTPS三文件与本地逐字节一致；正式浏览器刷新正常，资源版本为`20261019-work-orders`，新解锁区与套数说明已在DOM中。只检查公开页面，未登录账户或触发付款。
- 订单标题增加旧后台兼容：根据已知商品套数显示“3套制作额度”，不再直接采用旧catalog中的“27张”名称；JS十项回归与语法检查通过。
- 2026-10-20公网API仍返回`pack_prompt_version=v0.9-human-silhouette`、邮箱前置和素材保留开启，但`order_workflow`缺失，说明新增后台未重启加载。新前端门控继续禁止余额解锁与绑定作品付款；不能宣称完整订单新流程已在正式环境生效。
- 发布证据和截图留在私有`.local-data/order-works-audit-20261019/`。官网发布授权不等于同意消耗账户套数或发送交付邮件。

## 验证与限制

- 完整Python89项通过；新增15项包含并发幂等、指定作品、余额与关联、退款、重复交易review及重新有效解锁交付。
- JavaScript10项通过，含旧后台门控、generation_id传递、额外付款review和额度保留文案。
- 本地真实demo API加公开猫咪样例复现：原页面三套误示27张；新版选指定作品、余额3→2、作品解锁、邮件队列、订单使用去向均通过。模拟邮件SENT不代表生产邮件已发送。
- 浏览器证据在私有`.local-data/order-works-audit-20261019/`，不是生产账户登录截图；未声称390px或完整无障碍验收。
- 风格/动作/微信PNG等质量限制见既有质量交接。本次不启动新的付费生图或真实扣款。
