# 2026-10-18 Overlay + One page 上线

用户决定支付采用 Overlay + One page，并明确授权发布上线。

- `app.js` 的 Paddle 初始化默认设置及每次打开结账均设置 `displayMode: 'overlay'`、`variant: 'one-page'`；覆盖首次解锁、Pack 购买、继续待付款订单和 `_ptxn` 支付链接恢复。
- `index.html` 的 app.js 缓存版本更新为 `20261018-one-page-checkout`。邮箱验证、服务端支付核验与邮件交付流程沿用现有实现。
- 项目 main 提交 `df2bd7c` 已推送；从官网远程 main 创建临时隔离源码目录，仅同步 `sticker/app.js` 和 `sticker/index.html`，官网源提交 `faf8bd40c7058433f3efab7e6956a18a996ae0b6` 已推送。
- 官网同步工作流 `39099194416` 和 i18n 检查 `39099194415` 均成功；公开站点同步提交 `741f8e2155ff782dff6d4555d913920890e80a55`。
- 正式页面 `https://wisteriasoftware.uk/sticker/` 与新版脚本 URL 均成功读取，字节内容与本地一致。index.html SHA-256：`7b7e66184f1fcb8d537c3bfbfd75649e4bb1104a083d006acec920463d4dc1b5`；app.js SHA-256：`cd7e1dd2f3f2cd4323028ebc3a70548d4e2673d331a3e12fe5f0e5ef2db45f20`。
- 本地 `node --check app.js`、5 项支付监控回归及初始化／首次解锁／Pack 购买／继续订单的结账参数检查通过。

本次仅发布前端，无需更新后端或重启服务。未执行真实付款，公网文件核验不代表实际付款与邮件完整验收通过。未发布配置、凭据、`doubao/`、`UI/` 或用户未提交的研究文档。
