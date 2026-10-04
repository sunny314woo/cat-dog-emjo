# My Pet Stickers / cat-dog-emjo

- 本目录是独立 Git 仓库，远程为 `git@github.com:sunny314woo/cat-dog-emjo.git`，不是外层 `wisteria-suite` 的普通受跟踪目录。Git 操作必须在本目录执行。
- 新版首发 H5，目标使用 `https://wisteriasoftware.uk/sticker/`，与 Outline 官网同域名；旧 `pet.wisteriasoftware.uk` 为历史站点。正式路径发布前核对。只修改本项目文件，中文沟通。
- 需求以 `docs/PROJECT_OVERVIEW.md` 的 V2.3 整理稿为主：首版九张，匿名生成、免费任选两张正式贴纸，完整解锁时邮箱验证码账户，支付确认后同一套九张、切图及邮件交付；后续生成消耗 Pack。Python／FastAPI／MySQL／pymysql 原生 SQL，禁止 ORM。账号／语音服务 `services/account-server` 和 Outline `services/api-server` 只读参考；后端独立部署，不影响同台其他服务。
- 当前 Prompt 规范是 `PET_STICKER_PROMPTS.md` 前半部分的 v0.5；v0.1 附录仅供历史比较，不与活动模板一起注入。
- 保留全部既有风格。Prompt 库有十三种候选，UI 每次展示四种，最终组合未定。每种三个变体见 `docs/research/sticker-styles-2026-10-02.md`。表情包支持9/18/27张分页，小配饰可选；首版每次处理一个指定主体。
- 2026-10-03 最新用户决定采用方案 A：1–3 张同一主体原照片先生成一张个性化四风格母图，裁成四张供选择；再以原照片 + 选中单张风格参考 + 九项动作生成一张九宫格。两次生图，不把四种风格同时注入第二阶段，不开放自由 Prompt，不逐张 AI 补画。原照片不能被示例替代。2026-10-04 两阶段代码已部署，真实模型质量和完整流程仍待验收；替代此前固定样例直接九宫格的产品合同。
- `doubao/` 是本地实验与旧提示词，`UI/` 是本地设计参考。两者可能包含凭据，整个目录禁止提交、推送或复制到公开网站。不要输出 API key。
- 凭据只放本地环境配置；`.env.example` 只允许空值或占位符。`.local-backups/` 仅本地备份，不提交或发布。
- 官网两阶段前端已发布，后端运行 live 模式；当前模型可用性和真实输出以交接文档及实测为准。下载 Prompt 文档、模拟测试和服务启动均不代表真实生成已通过。透明处理使用本地 rembg，不宣称模型支持原生透明输出。
- 获取远程更新优先 `git fetch origin` 后检查差异；工作区干净且可快进时使用 `git pull --ff-only`。不覆盖本地改动，不对凭据使用 `git add -f`。
