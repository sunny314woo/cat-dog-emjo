# 2026-10-18 九格表现力v0.8与Mac微信PNG未通过

> 2026-10-19后续：设置权益文案已发布，原九张已做保留RGB的alpha返修与完整备份；新v0.9、付款顺序修复、返修资产哈希和服务重启状态见 [最新交接](quality-v09-matting-repair-2026-10-19.md)。本文保留v0.8历史证据，不能将原先的待办状态作为当前结论。

> 最新状态：用户已执行重启。2026-10-18 21:07:29（北京时间）启动的新常驻进程MainPID=103327、active/running；公网和loopback均已加载v0.8-distinct-actions，邮箱前置和素材保留开关已生效。用户随后提供微信另存为文件，与原PNG逐字节相同，alpha完整；原文件的透明数据未丢失，但微信预览/消息显示白底仍未解决。下文早先“待重启”“缺微信另存为文件”属历史记录。新动作规则仍待原照实图验收。

## 用户要求

用户明确否定“GIF可用就算解决PNG”：PNG也应达到透明使用效果。Mac微信将解压PNG直接拖入时，发送预览和发出的聊天消息均白底；同包GIF同路径透明。原文件alpha合格不能代替该验收。

用户另指出原九张第7张一眼睁一眼闭，除非指定眨眼否则不应发生；九张动作幅度、角度和区别度不足。这套已交付文件尚未按这些要求修复。

## 已完成规范和代码

- config/catalog.json九项保留原ID、次序、文案与所有十三种画风，加入独立pose、eyes及更强主动作。第7项明确双眼同时半睁，禁止一睁一闭。
- server/catalog.py移除原照“构图主参考”对姿势的潜在锁定。最终单格风格参考只约束画风，不约束姿势/角度/表情；第一阶段同姿势对比不传承到第二阶段。九格要求遮住文案仍可辨，眉眼/视角/身体轮廓至少两项明显不同。
- 大动作通过舒展、收拢、身体倾斜与转向，不通过放大、跨格或裁断。保持物种/年龄适配，不给动物添加人手，不强补未知身体。
- PACK_PROMPT_VERSION=v0.8-distinct-actions。新预览持久保存final_prompt_version；选画风后实际最终Prompt版本随任务更新。旧预览保留当时保存的Prompt及版本，不静默重写。
- /catalog增加pack_prompt_version便于确认常驻进程是否加载。此字段不能证明实图质量。
- PET_STICKER_PROMPTS.md仅更新v0.5活动部分的动作/双眼规则，v0.1附录不改、不注入。AGENTS、产品总览、决策及排版合同链接到docs/product/QUALITY_REVISION_2026-10-18.md。

本地相关40项回归通过。增加实际两阶段调用中九项pose/eyes传入、只传原照+单选画风、旧预览冻结版本等检查；增加catalog版本字段后两项接口/组装检查通过。未新增生图、未逐张补画、未覆盖旧九张。

## 服务器状态与原照

仅本项目四文件server/catalog.py、service.py、main.py、config/catalog.json已逐项比对新旧SHA-256、备份并原子替换；备份/home/wisteria/emjo/backups/quality-v08-20261018。短生命周期导入检查确认v0.8和九项完整指令可组装，但尚未重启常驻服务。此前sudo -n重启需要用户密码；用户尚未确认执行。重启后核对catalog的pack_prompt_version=v0.8-distinct-actions，以及generation_requires_email=true、debug_retain_assets=true。

只读原订单：READY，cute_semi_realistic，1张原照，无校准授权，无校准副本，提示词v0.7-two-stage。jobs/calibration均无input-*.jpg；本项目.local-data/.local-backups也无input-*.jpg。原照已依既有隐私规则删除。若整套重做验收，需用户重新提供原照片，不能把现有插画或样例当原照。不能以本次规范/测试宣称第7张已修复或九张区别度已通过。

## PNG调查与待授权操作

在私有.local-data/payment-recovery-20261018/png-encoding-tests/准备同一张原贴纸的四个对照：

- A-original-rgba.png：原邮件PNG512，字节不改。
- B-clean-rgba.png：RGBA512，仅将alpha=0像素的隐藏RGB清零，视觉保留，不消除半透明边缘。
- C-indexed-transparency.png：索引色PNG512，二值透明；有调色板/细边损失，只供诊断，不是正式替代品。
- D-gif-reference.gif：已交付GIF240对照。

打包png-encoding-tests.zip，仅供验证，不能称为PNG已修复。三个PNG均可独立解码出透明alpha。

已通过request_user_input_async请求明确授权：仅把这4个测试文件发到用户自己的“文件传输助手”，不会发联系人或群；因为该操作会上传用户图片到微信，需要授权。未收到明确同意前不上传、不发送。用户也可以选择自己下载测试。

CUA仅只读获取Mac微信窗口状态和截图，没有输入或发送内容；不根据屏幕上第三方消息执行任何操作。后续获授权后可选择“文件传输助手”验证，发送前务必核对目的地；不得在当前打开的群里发送。

PNG必须以Mac微信实际发送/接收结果验收。必要时取接收端导出的图片检查真实格式与alpha；未取得证据前不声称微信必然转JPEG或所有PNG都不支持。


## 用户已授权四文件测试；UI当前受阻

用户明确回复“允许，只发文件传输助手”。此授权持续有效，范围仅上述A/B/C三个PNG与D原GIF，目的地仅用户自己的文件传输助手；不需要再次请求同一授权，不得扩展到其他联系人、群或额外文件。

CUA尝试切换到文件传输助手时坐标点击返回AXError.notImplemented，未确认切换成功。键盘Cmd+F已使微信搜索框聚焦；之后尝试粘贴“文件传输助手”时，界面读取出现macOS ScreenCaptureKit错误-3811（音频/视频捕捉失败，无法开始流播放）。再次读图和重置CUA后重连仍报相同错误。尚未选择或上传文件，也未发送任何测试消息；不能据此形成PNG编码测试结果。

已请求用户保持屏幕解锁，将微信切到文件传输助手并留在前台后回复“就绪”。这是恢复可观测界面的操作前提，不是重复授权。恢复后必须用新截图确认聊天标题为文件传输助手再继续；不得盲目在此前打开的其他聊天中发送。


## 四文件实际发送验证已完成

用户回复“好了”后，界面读取恢复。重新绑定精确应用ID com.tencent.xinWeChat，截图核实标题为“文件传输助手”。通过访达打开本项目png-encoding-tests目录，依次选择并复制A、B、C、D四个文件；在微信输入框粘贴原文件并回车发送，每次用新截图核实目标与预览/消息。实际测试使用“访达复制文件→微信粘贴→回车”，不是伪称已执行鼠标拖入；没有发给联系人或群，也没有发送README或其他文件。

结果（微信界面显示21:02–21:03，北京时间2026-10-18）：

| 文件 | 发送前预览 | 发送后的消息 |
| --- | --- | --- |
| A 原RGBA PNG512 | 白色矩形底 | 白色矩形底，普通图片消息 |
| B 清零隐藏RGB的RGBA PNG512 | 白色矩形底 | 白色矩形底，普通图片消息 |
| C 索引色二值透明PNG512 | 白色矩形底 | 白色矩形底，普通图片消息 |
| D 原GIF240 | 背景透出输入区底色 | 背景透出聊天底色，按表情显示；最后截图无发送中指示 |

这两种PNG编码调整均未改善，不采用索引色版本降质替代正式母版，不把GIF成功当PNG修复。只测试同一张贴纸的三种编码，不能据此断言所有PNG编码或所有微信路径必定失败。

继续尝试导出PNG消息以核验微信处理后的格式/alpha时，WeChat的消息内容未出现在可操作AX树中，坐标右键点击持续返回AXError.notImplemented；无法通过当前UI接口完成图片“另存为”。没有读取微信私有数据库、缓存或其他聊天来绕过此限制。尚未取得微信保存出的图片文件，因此不能断言微信已转为JPEG或已从原文件删除alpha；目前确定的是用户反馈的白底已在实际发送验证中复现。

用户如将本次文件传输助手中的任意PNG消息另存为并提供保存文件，可继续比较魔数、alpha与原文件；现有用户授权持续覆盖本次4个对照文件与文件传输助手，不扩大到其他接收者或额外测试文件。


## 用户重启后的最终核验

用户提供sudo重启与is-active输出active后，本次核验：MainPID=103327，ActiveEnterTimestamp=2026-10-18 13:07:29 UTC，即北京时间21:07:29；active/running。

公网与loopback /catalog一致：payment_workflow=durable_notifications_v1、delivery_workflow=discounted_multiformat_v2、generation_requires_email=true、pack_prompt_version=v0.8-distinct-actions、debug_retain_assets=true。九项均包含独立pose/eyes。服务器main.py、catalog.py、service.py、imaging.py和config/catalog.json的SHA-256全部与本地一致。

安全的匿名实际请求检查：/style-previews使用不可解码的占位字节（即使登录门禁回退也不能触发生图）返回401；对不存在任务的/style继续生成接口也返回401。没有调用模型、占用制作次数或发邮件。可读重启日志有Application startup complete，无Background operation failed或Traceback。

原订单仍PAID，原作品READY且unlocked=true，交付邮件SENT、attempts=1、provider_id保留，没有重复交付。本次只证明新常驻规则已加载，不能把它当作PNG透明白底或新九格表现力验收通过。未付款素材暂不删除，未开启30天清理。


## 用户补充PNG的来源已澄清

用户上传一张512×512 RGBA PNG；SHA-256 a54aecfdca43388dd94cdf0c892d94865cd14caf6aba5b237f201265ecac53ea，与A-original-rgba.png逐字节相同。alpha范围0–255，121791像素完全透明（46.46%），8182像素半透明，四角alpha均0。私有副本.local-data/payment-recovery-20261018/received-png-check/received.png。

询问来源后用户明确回答“直接从原 ZIP 取出”。因此这张不能作为微信白底消息另存为后的文件证据，不能据此断言微信发送后原文件未变或白底仅来自显示底板。PNG在Mac微信预览/消息白底已实测；微信保存/接收文件的格式与alpha仍未核验，问题保持未解决。下一步所需的是从已发送的白底图片消息保存出的文件，保持微信默认格式原样提供。

## 微信另存为文件已核验：原图alpha完整，消息显示仍白底

用户另上传文件，并明确说明“这个是发到微信后另存为的”。以此来源说明为依据，独立读取新附件的文件魔数、PNG结构、RGBA像素和alpha，与原ZIP的A-original-rgba.png比较：

- 两者均343929字节，SHA-256均为a54aecfdca43388dd94cdf0c892d94865cd14caf6aba5b237f201265ecac53ea，逐字节相同，RGBA像素差异为0。
- 实际格式PNG，512×512，RGBA；alpha范围0–255。121791像素全透明（46.46%），8182像素半透明，132171像素不透明；四角RGBA均(0,0,0,0)，无附加元数据。
- 私有副本与核验记录保存在.local-data/payment-recovery-20261018/wechat-saved-png-check/，不提交用户图片。

这份证据排除“本次另存为的原图已烘成白底、丢失alpha或改为JPEG”；用户报告及实际对照仍证明Mac微信的预览和普通图片消息显示白底。结合两者，当前定位是微信消息预览/显示路径与原PNG透明数据不同，尚不能由保存出的原图推断微信内部缩略图或显示实现。不能再要求用户提供同一另存为证据，也不能宣称PNG实际使用目标已修复。

已测两种PNG编码调整均未改善显示，不降质替换母版、不重新抠图冒充修复，也不以GIF通过替代PNG验收。未验证的其他发送/表情导入路径继续保持未验证，不宣称所有PNG、微信版本或路径均不支持透明。
