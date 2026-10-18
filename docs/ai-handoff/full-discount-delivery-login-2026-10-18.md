# 2026-10-18 全额优惠交付恢复、登录前置与保留规则

## 原因与线上订单恢复

用户反馈10月4日创建的首次解锁订单仍显示“待完成”，已收到Paddle发票但没有贴纸交付邮件。

只读核对生产后确认：10月18日对应Paddle交易completed，custom_data订单号、价格、商品和数量均匹配；签名通知已被后台接收。交易原价USD10，合法全额优惠USD10，应付0。旧代码的total<=0拦截将通知置于REVIEW，订单仍PENDING，未创建邮件。不是用户未完成结账。

已通过存储的原签名通知与重新读取的Paddle实际交易，使用修复后的Service.complete_payment重处理该订单：订单PAID，原关联READY作品unlocked=true，无新生图，无额外Pack。原review保留并标记verified_full_discount已解决，notification置DONE。

- 原九张512PNG字节未改，原ZIP及相关私有记录已备份。
- 新ZIP 8,339,587字节，SHA-256 `a86cf233e4892ff7de2412fb55591848bea3f56b97d4d2b15bbb0f3af1b38248`。
- ZIP内47项：同一套九张的五组版本（45个贴纸文件）+grid.png+README.txt。PNG512根目录，PNG256/PNG240/GIF240/WebP512分目录。
- 下载后逐项验证45个贴纸文件尺寸、alpha含0且有有效前景、外围完全透明；512PNG与原交付包逐张字节一致。未宣称轮廓语义无瑕疵或手机聊天导入已验收。
- 正式交付邮件SENT，首次成功，provider_id已持久化；Resend只读返回last_event=delivered（收件服务器接受），附件列表确认为my-stickers.zip、8,339,587字节。用户随后已确认收到邮件；但反馈实际测试PNG出现白底、GIF透明，实际使用的设备和应用/导入路径尚待确认，透明交付的用户端验收仍未通过。
- 私有证据在本项目被忽略的.local-data/payment-recovery-20261018；服务器备份/home/wisteria/emjo/backups/delivery-login-20261018。不公开这些素材、记录或签名下载链接。

## 已实现

项目提交 `b71197e` 已推送cat-dog-emjo/main。

- 零总额仅在completed、原订单/商品/价格/数量匹配、存在折扣、正小计、优惠恰好覆盖小计与税、grand_total/balance均零、币种一致时允许。异常保留人工核验，正额与退款、幂等逻辑保留。
- 后台通知保存匹配订单ID；账户历史/订单查询区分REVIEW、CONFIRMING；前后端阻止核验中的订单重复结账。
- 新作品ZIP增加所有既有交付格式；导出九张母版检查真实透明和外围。临时目录完整打包后原子替换，失败保留旧ZIP。
- 首页先验证邮箱再上传；生成按钮补充登录检查与登录后续接。live后端风格预览/直接生成/继续风格均验证登录，重试次数绑定邮箱账户。demo固定样例仍可匿名；同邮箱多设备不重置资格，不宣称防止同人多个邮箱。
- 设置中我的作品/订单移到登录后内容的上方；说明多格式交付；付款监控更新历史。
- 用户决定“未付款作品先不删，后续约30天”已写入docs/product/DECISIONS_2026-10-18.md、AGENTS.md、PROJECT_OVERVIEW.md及部署说明。当前debug_retain_assets=true保持不变，无清理任务；未来启用时旧作品需约30天过渡，不能直接释放旧expires。原照删除/撤回校准仍遵守原隐私规则。

## 验证与发布

- 后端57项回归通过，包含全额优惠首次解锁与单次邮件、7组无效零额拒绝、live匿名拒绝及同邮箱跨设备限次、多格式ZIP透明/原子性；随后加强的REVIEW订单后端禁止重复结账测试单项通过。
- 前端6项支付监控测试通过，node语法与git diff --check通过。
- webapp-testing：390px手机视口，358px设置弹窗，无横向溢出、无JS报错；首页验证邮箱后回到上传；作品/订单在登录与邮件上方；核验异常不展示继续付款。样例环境，不发送真实验证码邮件或付费生图。
- 官网只更新sticker/app.js与sticker/index.html，源码提交 `5fbfd30aa91dacb2e50555be722de344edd15049`；i18n工作流39100264531和同步工作流39100264530均success。正式/sticker/与带20261018-delivery-login版本脚本的SHA-256均与本地一致。
- 后台3份代码（server/main.py、service.py、imaging.py）已校验SHA-256、编译、备份并原子替换至current。一次性订单恢复进程使用了新版Service；常驻服务仍是旧进程。

## 尚需用户重启独立服务

`sudo -n systemctl restart emjo.service` 返回“a password is required”。用户需在服务器终端执行：

```bash
sudo systemctl restart emjo.service
sudo systemctl is-active emjo.service
```

截至2026-10-18 13:23（北京时间）只读核对：MainPID仍4102531，启动于10月12日21:06；公网catalog没有delivery_workflow/generation_requires_email，debug_retain_assets=true。因此**不能声称常驻后端已启用新的全额优惠和登录规则**。订单解锁与正式邮件交付已经成功，不依赖这次重启。

收到用户执行结果后检查公网和loopback catalog：delivery_workflow=discounted_multiformat_v2、generation_requires_email=true、debug_retain_assets=true；核对MainPID/启动时间和该订单PAID/unlocked/mail SENT。不得为验收新增生图、代付或重复发送已成功邮件。不要修改其他服务。


## 用户收件后的 PNG 白底反馈（2026-10-18）

用户确认已收邮件，但反馈 PNG 看起来有白底、GIF 透明。尚未说明设备、应用、是否经相册保存/微信普通图片发送/自定义表情导入，不能直接归因为用户操作或预览底色。

本次进一步直接读取 Resend 保存的已发送 ZIP 附件（不是仅检查服务器当前文件）：SHA-256 与交付包一致。附件内首张 PNG512 为 RGBA、46.46% 像素 alpha=0；PNG240 为45.11%；GIF240 为48.35%。九张 PNG240 与 GIF240 对比，GIF 完全透明区域恰好多出 PNG alpha 1–127 的半透明像素；PNG 外部 alpha=0 的位置没有在 GIF 中变成不透明。九张原 PNG 合成绿/深色底均能透出底色，无整幅白色矩形底；仍有应与透明通道分开评估的轮廓白边/局部碎片。

诊断图和指标位于私有 .local-data/payment-recovery-20261018/png-gif-diagnosis/。不修改原图、不把所有白色像素变透明（会误删白衣和文字描边），不重复发送同一邮件，不据文件 alpha 检查宣称手机聊天导入已通过。

已向用户询问设备和实际查看/发送路径，收到回答后沿该路径继续排查。后台 catalog 仍无新版字段，用户的收件反馈不是重启完成确认，重启待办保留。
