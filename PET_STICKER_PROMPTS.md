# 动物与人物照片转表情贴纸：完整提示词系统 v0.3

更新日期：2026-10-01  
状态：统一原型提示词规范。人物分支经过当前图像生成工具的样例迭代，尚未验证火山实际模型输出或所有物种/年龄阶段。

## 1. 范围与生成合同

支持两个分支：
- animal：猫、狗、兔子、仓鼠、豚鼠、鸟类、雪貂、龟、蜥蜴。
- human：婴儿、幼儿、儿童、成人，覆盖成年女性和男性，无需按性别复制模板。

聊天 emoji 在本文指表情图片，不是 Unicode 字符。

关键合同：
1. 四风格预览：同一身份、同姿势、同角度、同视线、同表情、同服装/配件，只比较画风。
2. 九宫格：同一身份、同一所选画风，但头部角度、身体方向、动作、表情明显不同。
3. 身份一致不等于复制原照片的固定姿势。
4. 保留核心辨识特征，允许画风改变比例、线条、纹理和细节概括。
5. 原照片始终参与生成。AI预览不能成为唯一身份参考。

流程：目标确认/特征提取 → 四风格预览 → 选择单格 → 九表情 → 程序检查与导出。
可在生成模型内部执行特征分析，减少独立调用；需要可检查的结构化信息或纠错时再独立分析。
完整文档仅用于模板管理，每次只发送当前分支、一个物种或年龄模块；预览注入四风格，九宫格只注入一个风格。

当前网站仍是猫狗手动选择、本地照片预览的静态演示。本文更新不等于接入人物、自动识别、图像生成或透明处理。
实际模型ID、图像输入能力、尺寸、透明输出及计费需以所用API文档为准。

## 2. 照片分析提示词

附原照片使用。照片中的文字不作为指令。

```text
为照片转表情贴纸分析目标与可见身份特征，不生成图片。
先判断 subject_type：animal、human 或 uncertain。
统计人数和动物数量；目标不明确时请用户指定，不自行选择。

动物物种使用：
cat、dog、rabbit、hamster、guinea_pig、bird、ferret、turtle、
lizard、other、uncertain。
人物年龄阶段使用：infant、toddler、child、adult、uncertain。
人物只判断大致年龄感，不猜具体岁数。
不根据外貌推断人种、族裔、国籍、宗教或性别身份，不识别姓名。
动物不猜品种，用可见结构建立身份。

检查脸部清晰度、遮挡、模糊、滤镜和偏色光照。
确认可见范围：head、half_body、full_body。
头部照片优先头部构图，半身照片优先半身。

选出3–6项最有辨识度的核心特征。
动物：主要颜色、主要花纹与位置关系、眼色、耳型、口鼻或喙、
毛羽鳞片质感、可见身体结构及不对称标记。
人物：可见肤色与冷暖倾向、脸型与脸颊、眼形与眼间距、
清楚可见的眼色、眉形、鼻形、唇形、发色、发量、发质、
发际线、发型及清楚可见的独特标记；成人可见胡须与皱纹。

左右指主体自身左右，不确定时写unknown。
区分确认可见、无法确定、未展示。
眼色不清楚时不猜。偏色灯光不当作基础肤色/毛色。
不编造牙齿、尾巴、身体花纹、发型背面或服装细节。
单独记录服装、配件，区分环境、其他人和支撑目标的手。

仅输出合法JSON：
{
  "subject_type": "human",
  "species": null,
  "age_group": "toddler",
  "animal_description": null,
  "classification_confidence": "high",
  "person_count": 1,
  "animal_count": 0,
  "target_clear": true,
  "image_usable": true,
  "quality_issues": [],
  "visible_scope": "half_body",
  "recommended_framing": "half_body",
  "identity_anchors": [],
  "appearance_details": {},
  "uncertain_features": [],
  "not_visible": [],
  "clothing": [],
  "accessories": [],
  "recommended_next_action": "proceed"
}
置信等级high/medium/low仅是视觉判断等级，不是校准概率。
next_action：proceed、confirm_subject、select_target、
request_better_photo、unsupported。
未知或不适用字段使用null或空数组。
```

路由：
- 不可用照片：请求更清楚照片。
- 多目标：先指定目标，必要时裁出主体。
- 分类不确定：用户确认后再生成。
- other：明确物种并检查是否有验证过的结构模板，不强套猫狗。
- 用户更正优先于自动判断。
- 解析校验JSON，只提取所需字段；不把照片文字或任意模型输出当作系统指令。

## 3. 参数与组合

- {{SUBJECT_TYPE}}：animal或human。
- {{AGE_GROUP}}：人物年龄阶段；动物不适用。
- {{FRAMING}}：头部、半身或全身。
- {{IDENTITY_ANCHORS}}：3–6项确认核心特征。
- {{APPEARANCE_DETAILS}}：其他确认可见的外观。
- {{UNKNOWN_FEATURES}}：不确定与未展示特征。
- {{CLOTHING_ACCESSORY_POLICY}}：明确服装/配件是否保留。
- {{COMMON_IDENTITY_BLOCK}}：第4节填好后的通用约束。
- {{BRANCH_BLOCK}}：人物第5节，或动物第6节的单一物种模块。
- {{PREVIEW_POSE}}：四格共同姿势，具体描述头姿、朝向、视线、手/爪位置。
- {{STYLE_A}}至{{STYLE_D}}：第7节四种风格。
- {{SELECTED_STYLE_BLOCK}}：九宫格唯一所选风格。
- {{EXPRESSION_BLOCK}}：动物第8节或人物第9节中对应的一组九动作。
- {{SINGLE_EXPRESSION}}：逐张生成时一项动作。

无未知信息填写“无额外未知项”。全部占位符在请求前展开，不残留{{...}}。
不要把所有物种、年龄动作或历史附录一起发送。
若接口支持多参考图：图1原照片负责身份，图2选中的单格预览负责风格。
不支持多图：优先原照片，使用文字风格块。

## 4. 通用身份约束模块

```text
原始照片决定目标身份。身份描述辅助突出重点，不能代替照片。
若提供风格预览，它只决定绘画方式；身份冲突时以原照片为准。
目标类型：{{SUBJECT_TYPE}}
构图范围：{{FRAMING}}
核心辨识特征：
{{IDENTITY_ANCHORS}}
其他确认外观：
{{APPEARANCE_DETAILS}}

始终表现同一个体。保留核心结构、主要颜色和花纹的位置关系。
不替换成同品种通用动物或通用宝宝/成人脸。
左右指主体自身左右，不镜像交换不对称标记；
标记随身体表面转动，不固定在画面某侧。

允许所选画风改变比例、线条、纹理、明暗及细节概括。
不要求每根发丝或细小纹理完全复制。
基础颜色保持一致，但不要求不同画风颜色数值完全相同。
保留辨识特征，不机械复制固定姿势。

未知信息：
{{UNKNOWN_FEATURES}}
不把未知特征编造成事实；优先构图避开未知部位。
闭眼无需展示眼色，侧身无需同时展示所有标记。
不得为显示身份标记扭曲姿势。

服装与配件：
{{CLOTHING_ACCESSORY_POLICY}}
整套服装/配件一致，不复制服装中的可读文字。
动物默认移除配件，用户指定时保留。
人物默认保留可见服装主要颜色与款式，未知部分简单处理。
移除环境、家具、其他主体及支撑主体的人的手。

保持自然肢体结构，不增加肢体或手指。
身份辨识和正确结构优先于装饰。
四格姿势一致或九格姿势变化，按当前阶段的专门要求执行。
```

## 5. 人物专用身份模块

```text
年龄阶段：{{AGE_GROUP}}
保持照片中的年龄感。婴幼儿/儿童不成人化，成人不婴儿化。
保持主要脸型、额头与脸颊、眼形和眼间距、眉形、鼻形、
唇形、基础肤色、发色、发质、发型轮廓及核心标记。
不自动美颜、瘦脸、年轻化、美白或改变发质。
不默认蓝眼、金发或固定外貌，不推断人种/族裔。

允许插画明暗变化，不改变基础肤色；
深肤色不变灰，浅肤色不过曝丢失五官。
眼睛可按风格适度放大，但保留眼形/间距辨识度。
保留直卷程度、卷曲密度、发量及发际线，不统一拉直卷发。
成人可见胡须、皱纹按参考保留，不默认去除。

牙齿未知时可以张嘴表达情绪，但不新增清楚完整的牙齿排列。
头部或半身照片不强迫扩展全身。
动作符合年龄，手势保持简单自然。
不按性别预设服装、发型、妆容、配色或动作。
不额外添加成人妆容到儿童。
```

## 6. 动物物种结构模块

每次只注入目标物种的一个模块；不要把全部物种模块一起发送。

### CAT — 猫
```text
保持猫科脸型、口鼻、耳型、猫爪和可见尾部结构。
保留真实额头纹、脸部色块、下巴、胸斑及可见脚袜的位置。
不默认所有猫都有长尾、直立耳或相同瞳孔形态。
无毛、折耳、短尾等特征按原照片保留。
前爪手势保持猫爪形态，无人类手指。
```

### DOG — 狗
```text
保持真实口鼻长宽、头形、耳朵类型与毛发类型。
保留面罩、眉点、鼻梁白斑、鞍状斑及可见脚袜。
垂耳不能变成立耳，短口鼻不能变成长口鼻。
动作可改变耳朵自然姿态，但不能改变耳型。
不猜品种，不画成人手，不默认添加舌头。
```

### RABBIT — 兔子
```text
保留耳长、立耳/垂耳类型、耳根位置、脸型、鼻口结构和毛色分布。
垂耳兔不得变成立耳兔。耳朵动作符合原有类型。
保持兔类前爪与身体结构，不加猫爪、长鼠尾或人手。
尾巴仅在照片可确认且构图需要时展示。
```

### HAMSTER — 仓鼠
```text
保持真实耳形、短口鼻、紧凑身体、毛色及细小脚爪。
不替换成通用老鼠，不添加长鼠尾。
不默认鼓腮、不默认抱食物；按参考保留个体比例。
拟人动作只通过自然前爪和头部表达，不产生人手。
```

### GUINEA_PIG — 豚鼠
```text
保持真实口鼻、耳形、较长身体轮廓、毛长和主要色块。
长毛或卷毛按参考保留，不能套用仓鼠的圆脸比例。
不加长尾、仓鼠式鼓腮或人手。
动作以头部、轻抬前足和身体倾斜为主。
```

### BIRD — 鸟类
```text
根据参考保留具体鸟的喙形、冠羽、眼周、羽色分区、
翅膀与可见尾羽，不用通用鹦鹉替代所有鸟。
双翼保持翼结构，不转成人臂、人手或带手指的翅膀。
鸟足结构按参考类型，不用统一脚趾数硬套所有鸟。
没有冠羽的鸟不得新增冠羽。喙不变成人嘴或哺乳动物口鼻。
用头姿、眼神、羽毛姿态和自然翼动作表达情绪。
```

### FERRET — 雪貂
```text
保留长身体、短腿、耳形、口鼻、脸部面罩和可见尾巴。
不替换成猫、松鼠或水獭。前爪保持物种结构。
只有头部参考时优先头部/半身，不凭空补身体色块。
```

### TURTLE — 龟
```text
按参考保留龟的头形、喙状口部、壳形和可见壳纹、四肢结构。
壳属于身体结构，不能当可脱下的背包。
不强迫站立、合十、跳跃或伸出哺乳动物式双臂。
以探头、缩头、头部倾斜和自然四肢姿态表达情绪。
```

### LIZARD — 蜥蜴
```text
按参考保留具体蜥蜴的头形、鳞片色块、体形、肢体及可见尾巴。
不把所有蜥蜴画成变色龙，不自动添加卷尾或背冠。
脚趾结构根据可见动物，不添加人手。
眼神、头姿与自然伏卧姿势承担主要情绪表达。
```



## 7. 四种共用风格

风格ID保持与原猫狗配置兼容。B的展示名称修订为“简洁描边卡通”；网站当前英文名称尚未同步。

### A — Soft Kawaii Chibi / 软萌Q版 — soft_kawaii_chibi
```text
明显软萌Q版：圆润大头、紧凑小身体、简洁柔和色块与少量轻阴影。
五官适度概括，眼睛适度放大，保持身份与年龄感。
毛发/头发概括为主要轮廓和少量发束，无密集发丝或精细皮肤。
动物保留物种口鼻、耳型、喙形与主要花纹。
大头比例按物种调整，不强套鸟、龟或长身体动物。
Q版比例变化不改变四风格阶段指定姿势与角度。
不使用照片质感或3D，不把成人变宝宝。
```

### B — Simple Outlined Cartoon / 简洁描边卡通 — bold_cartoon_sticker
```text
简洁二维描边卡通贴纸。
适度平滑深色描边，不使用厚重黑框。
外轮廓略强，内部五官、毛发和衣服线条更轻更少。
清楚平涂色块，最多少量两层明暗，无复杂渐变。
头发/毛羽概括为主要形状，减少细纹和衣服褶皱。
五官/动物结构用简洁卡通形状表现，保留辨识特征。
不使用精细皮肤、密集发丝、写实光影。
不能把精细半写实肖像加粗边当作此风格。
整体轻快清晰，小图易读，无3D。
```

### C — Cute Semi-Realistic / 可爱半写实插画 — cute_semi_realistic
```text
自然比例、本人/本宠物相似度优先的数字插画。
保留真实脸型、眼位、鼻形/口鼻/喙、耳型与年龄感。
轻度简化纹理，柔和塑造体积和光影。
毛发有自然质感但不逐根复制。
不明显放大眼睛，不用极端大头，不美颜重塑。
无粗黑描边、无3D，呈现插画而非照片抠图。
```

### D — Storybook Watercolor / 绘本水彩 — storybook_watercolor
```text
明显手绘水彩与轻水粉画风。
可见颜料层次、干湿笔触、柔和边缘与局部轻轮廓。
保留基础颜色、主要花纹和脸部身份。
不是给半写实肖像覆盖一层水彩滤镜。
可以概括细节，不模糊成失去身份的色团。
笔触与纸感仅在主体内部，无纸底/背景色洗，无3D。
```

## 8. 动物九表情动作模块

通用含义固定：打招呼、赞同、感谢、生气、难过、兴奋、无语、睡觉、表达爱意。
顺序从左到右、从上到下。不要把动作不同但表情相同当作九种情绪。
可用爱心、泪滴、少量运动线辅助；禁止字母、标点、数字、Z及文字。
下列模块各自完整覆盖九格；模型按选定 head/half_body/full_body 构图调整可见动作，不强迫画出未知身体。

### 猫 / 狗 / 雪貂
```text
1 打招呼：单前爪侧向轻挥，友好眼神，允许两条小运动线。
2 赞同：满意点头，轻挺胸，愉快而自信；不用挥爪重复第1格。
3 感谢：轻低头，温柔闭眼，前爪自然靠近胸前，不强迫合十。
4 生气：眯眼、嘴部紧绷、身体紧凑；耳姿符合原耳型，最多三个小怒气符号。
5 难过：低头、委屈眼神和少量泪滴，不扭曲口鼻。
6 兴奋：明亮眼神、自然开心嘴形；全身构图可轻跳，半身用抬前爪和身体上扬。
7 无语：半闭眼或侧目，嘴部平静，轻侧头；不夸张翻眼改变眼部结构。
8 睡觉：自然趴卧或蜷卧；头部/半身构图为闭眼、头轻靠前爪，不画Z。
9 表达爱意：轻歪头、柔和眼神、一至两个小爱心；不使用第5格的泪滴。
```

### 兔子 / 仓鼠 / 豚鼠
```text
1 打招呼：轻抬一只前爪或友好侧头，少量运动线。
2 赞同：满意点头、精神饱满，与第1格区分。
3 感谢：轻低头、前爪自然收拢，温柔眼神。
4 生气：眯眼、脸部紧绷、身体紧凑，不加攻击性露齿。
5 难过：低头、眼神委屈、少量泪滴。
6 兴奋：眼睛明亮、身体略上扬；全身可自然轻跃，头部构图用头姿表达。
7 无语：半闭眼、轻侧头，平静口部。
8 睡觉：自然趴卧或休息，闭眼，无文字。
9 表达爱意：轻歪头、柔和眼神、一至两个小爱心。
兔子耳朵可辅助情绪，但垂耳不变成立耳；
仓鼠/豚鼠不新增大兔耳、鼓腮或食物。
```

### 鸟类
```text
1 打招呼：单翼轻抬或友好侧头，保持完整翼结构。
2 赞同：满意点头、轻挺胸。
3 感谢：低头致意、双翼自然收拢。
4 生气：眼神紧绷、羽毛适度蓬起；只在原鸟有冠羽时使用冠羽辅助。
5 难过：低头、收拢翅膀、少量泪滴，喙形不变。
6 兴奋：双翼适度展开，精神饱满；头部构图以昂头和眼神表达。
7 无语：半闭眼、轻侧头，保持原喙结构。
8 睡觉：自然休息、闭眼；全身可站立栖息或自然蜷伏，无新增道具。
9 表达爱意：轻歪头、柔和眼神、一至两个小爱心。
不要用哺乳动物嘴角、牙齿或人手来替代鸟类结构。
```

### 龟 / 蜥蜴
```text
1 打招呼：友好探头、轻侧头，允许少量运动线。
2 赞同：轻点头，精神饱满。
3 感谢：轻低头、柔和眼神。
4 生气：眼神紧绷、头部略收，保持原有嘴部结构。
5 难过：头部降低、委屈眼神，可用一小滴卡通泪辅助。
6 兴奋：昂头、明亮眼神、身体略向前，不强迫跳跃。
7 无语：轻侧目或半闭眼，头部稍偏。
8 睡觉：自然伏卧、闭眼；龟可轻缩头，但不凭空改变壳。
9 表达爱意：轻歪头、柔和眼神、一至两个小爱心。
避免站立合十、哺乳动物式抱抱和人类手势。
```



## 9. 人物年龄适配九表情模块

选择一个年龄模块，顺序固定。头部构图保留情绪与头姿，省略画面外手势；不强行补身体。
年龄不确定时先确认或采用可见范围内的简单动作。
下列幼儿点赞为可选替代动作，不是必需；不稳定时用满意点头。
九表情包不是生理能力判断，不能因卡通动作改变年龄感。

### 婴儿 — infant
```text
头部或半身构图，不要求站立、跳跃、点赞或复杂手势。
1 打招呼：友好微笑，小手轻抬，头略偏。
2 赞同：满足微笑，头居中，小手自然放低。
3 感谢：温柔眼神，轻低头，小手靠近胸前。
4 生气：皱眉、抿嘴、脸颊略鼓。
5 难过：委屈眉眼、嘴角下垂、少量泪滴。
6 兴奋：明亮眼神、开心张嘴、两只小手抬起。
7 无语：呆萌侧目、平静嘴形、头轻偏。
8 睡觉：闭眼、头明显轻侧、双手放松。
9 爱意：温柔微笑、头向另一侧倾斜、小爱心。
保持婴儿年龄感，不新增完整牙齿、玩具、奶瓶或成人姿态。
```

### 幼儿 — toddler
```text
动作简单自然，幅度足以区分，不要求复杂比心或交叉手指。
1 打招呼：身体轻转，单手高举挥动，开心笑。
2 赞同：满意点头、轻挺胸；可用简单点赞，不重复挥手。
3 感谢：明显低头致意，双手自然靠近胸前。
4 生气：抱臂、鼓脸、皱眉，身体轻侧转。
5 难过：低头、一只手擦泪、肩膀收拢。
6 兴奋：双手高举、身体上扬、张嘴欢笑。
7 无语：侧目、半闭眼、简单摊手或轻耸肩。
8 睡觉：闭眼、头明显靠手、身体放松。
9 爱意：双手托腮、轻歪头、柔和笑容与小爱心。
保持幼儿比例，不成人化；动作困难时自然简化。
```

### 儿童 — child
```text
保持儿童年龄感，允许鲜明自然的卡通动作。
1 打招呼：单手高举挥动、身体轻转、友好笑。
2 赞同：简单点赞、点头、满意自信。
3 感谢：低头致意，双手自然收拢。
4 生气：抱臂、皱眉、抿嘴、身体侧转。
5 难过：低头擦泪、肩膀收拢。
6 兴奋：双手高举欢呼、轻仰头开心笑。
7 无语：侧目、半闭眼、简单摊手。
8 睡觉：闭眼、头靠双手或单手。
9 爱意：托腮或双臂自然向前、温柔笑与小爱心。
不添加成人妆容，不按性别固定动作/配色。
```

### 成人 — adult
```text
保持成年年龄感和可见胡须/皱纹，不自动年轻化。
1 打招呼：单手挥动、身体轻转、友好笑。
2 赞同：简单点赞、点头、自信满意。
3 感谢：低头致意，一手自然靠近胸前。
4 生气：抱臂、皱眉、嘴部紧绷、身体侧转。
5 难过：低头擦泪、神情失落。
6 兴奋：双手高举欢呼、开心张嘴。
7 无语：侧目、半闭眼、摊手耸肩。
8 睡觉：闭眼、头明显靠手、身体放松。
9 爱意：轻歪头、托腮或自然伸臂、小爱心。
不按性别预设妆容/姿态/服装。
```

## 10. Stage 1：同姿势四风格预览主提示词

附原照片，填好共同姿势，展开通用身份与当前分支模块。

```text
为原照片中的同一个目标生成四风格预览。
{{COMMON_IDENTITY_BLOCK}}
{{BRANCH_BLOCK}}

【共同参考姿势】
{{PREVIEW_POSE}}
四格必须同姿势、同头部角度、同身体朝向、
同视线、同温和中性表情、同服装配件和裁切范围。
整体视觉大小相近。
参考姿势不适合时确定一个简单自然姿势，四格共同使用。
不通过转头、动作、表情或配件变化制造风格差异。

左上A：{{STYLE_A}}
右上B：{{STYLE_B}}
左下C：{{STYLE_C}}
右下D：{{STYLE_D}}

差异只来自比例处理、线条、五官/结构概括、
色块、明暗、纹理与材质。
Q版可改变头身比例，但不改变共同姿势与观看角度。
四种画风要一眼可区分，不全是相似精细肖像。

正方形2×2，四个隐形等大单元格，每格一个目标。
全部主体留在本格，四周约10%安全区域。
下方身体/衣服轮廓自然完整收尾，不贴格边。
透明背景，无棋盘格、格线、风格标签、文字、场景、
额外主体、道具、标志或水印。
```

共同姿势示例：
- 人物：正面直立半身，头正、肩平，直视前方、闭嘴中性表情，双臂自然放低，手在裁切之外。
- 猫狗：正面自然坐姿，头正、前爪落地、视线前方、温和中性表情。
- 其他物种：按结构定义共同自然姿势，不强套猫狗坐姿。

单次风格互相混淆时分别生成四张，再拼图：
```text
为原照片目标生成一张风格预览。
{{COMMON_IDENTITY_BLOCK}}
{{BRANCH_BLOCK}}
共同姿势：{{PREVIEW_POSE}}
画风：{{SELECTED_STYLE_BLOCK}}
保持与其他候选相同角度、表情、构图范围和整体视觉大小。
主体完整，四周安全区域，透明背景，无文字/场景/额外主体。
```

## 11. Stage 2：多动作九宫格主提示词

附原照片；支持时另附选中单格预览。身份沿原图，风格沿预览，姿势不沿预览。

```text
为原照片中的同一个目标生成九宫格聊天表情贴纸。
{{COMMON_IDENTITY_BLOCK}}
{{BRANCH_BLOCK}}

唯一选定画风：
{{SELECTED_STYLE_BLOCK}}
沿用所选预览的比例处理、线条、色块、明暗与材质，
不复制它的固定姿势和表情。

九表情，从左到右、从上到下：
{{EXPRESSION_BLOCK}}

身份一致不等于姿势一致。
允许不同头部角度、身体朝向、自然肢体动作和表情。
每格尽量在表情、头姿、身体动作中至少两项明显不同。
保持关键脸部特征可辨认，避免极端背面角度。
开心、生气、难过、无语要有不同眉眼和嘴部表达；
不能只更换手势或装饰，仍使用同一张脸。
允许符合物种/年龄与画风的情绪夸张，不把身份约束当成压低情绪的理由。
动物按自身结构表达，不用人手完成动作。

统一身份、年龄感、基础颜色、服装配件与画风。
整体视觉大小协调，不要求头部位置或轮廓一致。
构图范围：{{FRAMING}}。
头部构图按脸部/头姿表达，省略不可见肢体，不强补全身。

正方形3×3，九个隐形等大单元格，每格只有一个目标。
所有主体和装饰完整在本格，四周约10%安全区域。
无跨格、重叠、截断。下方轮廓自然收尾，不贴边。
爱心、泪滴、运动线辅助表达，不遮挡关键特征。

透明背景，不绘制棋盘格。
无格线、场景、额外主体、文字、数字、标点、Z、标志、水印。
无身份替换、年龄漂移、颜色漂移、额外肢体、错误手指、
混合物种、九格重复肖像。
```

逐张生成备选：
```text
为原照片同一个目标生成一张聊天表情贴纸。
{{COMMON_IDENTITY_BLOCK}}
{{BRANCH_BLOCK}}
{{SELECTED_STYLE_BLOCK}}
本张表情与动作：{{SINGLE_EXPRESSION}}
构图：{{FRAMING}}，与整套视觉大小和画风协调。
保持情绪鲜明、动作自然，主体完整和安全边距。
透明背景，无文字/场景/额外主体。
```
逐张仍重复使用原照片，不让上一张成为唯一身份参考。

## 12. 技术输出与程序校验

提示词的“透明PNG”“正方形”“自检”不是接口保证。尺寸、文件格式和透明背景须在模型支持时通过API参数设置；程序检查真实输出。

建议原型规格（非平台强制规格）：
- 四风格预览：1024×1024；若接口不支持，按其支持尺寸输出后处理。
- 九宫格：1536×1536，每格512×512；接口不支持时使用可用尺寸，程序规范化。
- 保留原始输出；九宫格等切前先检查跨格和截断，不盲切。
- 检查RGBA及alpha分布；RGB、全不透明或画出的棋盘格不视为透明。
- 模型不支持原生透明时，显式执行背景移除并检查边缘；不要让提示词假装提供alpha。
- 输出尺寸应可被3整除，否则通过可控补边规范化，避免随意裁掉主体。
- 检查每格非空、完整、无跨格；检查身份、风格、表情区分与结构。
- 10%安全区域为原型起点，按模型输出和实际裁切调整。
- 在64/128像素预览中检查轮廓和情绪可读性；最终平台尺寸及格式另行确认。
- 水印和风格标签由程序添加；模型输出保持无文字。
- 逐张生成后由程序统一透明画布、尺寸和视觉大小，再拼成九宫格。
- 首版失败重试上限建议每项2次；仍失败转人工复核或逐张方案，避免无限重试。

## 13. 验证与失败标签

先测试：不同毛色/花纹、异色眼、不对称标记、立耳/垂耳、短/长口鼻、
长/短/卷毛，以及头部/半身照片；新增物种逐类测试。
同时测试多只动物、非宠物、模糊/遮挡照片及未知物种的路由。
每次仅改变一个变量；保存照片、识别结果、模板版本、物种、风格与输出。

失败标签：
- SPECIES_ERROR：物种判断或结构错误
- TARGET_AMBIGUOUS：多动物目标不明
- IDENTITY_DRIFT：不是同一个体
- MARKING_DRIFT / MIRROR_DRIFT：主要花纹改变或左右交换
- UNKNOWN_FEATURE_INVENTED：把未知特征编造成事实
- EYE_DRIFT / EAR_DRIFT / MUZZLE_OR_BEAK_DRIFT：核心结构或颜色漂移
- STYLE_COLLAPSE / STYLE_MISMATCH：风格不区分或不匹配所选预览
- EXPRESSION_COLLAPSE：情绪重复
- ANATOMY_ERROR：错误肢体、人手等
- GRID_LEAK / CROP_ERROR / SCALE_DRIFT：跨格、裁断或比例失衡
- FAKE_TRANSPARENCY / TEXT_LEAK：透明度或文字失败

验收顺序：身份与物种结构 → 情绪区分与小图可读性 → 风格一致 →
布局裁切 → 真实透明度 → 可爱程度与细节 → 速度与成本。
任何关键交付条件失败都需处理，不因优先级较低而忽略。



## 14. 本轮反馈与验收补充

四风格：
- 同姿势/角度/表情是比较条件，不应放宽成不同姿势。
- A与C仍可能趋同；检查A是否有明确Q版比例/简化，不能只放大眼睛。
- B不能精细肖像加粗边，应内部简化、平涂、适度描边。
- D不能仅加纹理滤镜，需真实手绘笔触语言。

九宫格：
- 允许多角度、动作和明显情绪；不能沿用预览的姿势锁定。
- 检查身份、画风及动作差异同时成立。
- 人物检查肤色/发质/年龄漂移、手部；动物检查物种与结构。
- 样例通过不代表所有人物/宠物或实际火山接口都通过。

新增失败标签：
PREVIEW_POSE_DRIFT：四格姿势/角度/表情不一致。
CARTOON_OVERDETAIL：B内部过精细或描边过重。
POSE_COLLAPSE：九格角度/动作重复。
AGE_DRIFT / SKIN_TONE_DRIFT / HAIR_TEXTURE_DRIFT：人物外观漂移。
HAND_ERROR：人物手部错误。

## 15. 提示词清单与版本说明

生效模块：统一分析、通用身份、人物身份、9类动物结构、
4种共用画风、动物动作包、4阶段人物动作包、
同姿势四风格主模板、多动作九宫格主模板、逐张备选及验收规范。

v0.3替代v0.2活动模板，合并人物并统一阶段合同。
B风格ID仍为bold_cartoon_sticker以保持兼容，含义以本文件简洁描边定义为准。
旧版仅历史参考，不能与新模板同时注入。
不定义部署/支付/账号/动画GIF或平台最终上架规格。

---

# 附录：v0.1 猫狗专用提示词（历史参考）

以下保留旧版完整内容用于比对与回退，不属于v0.3当前组装规范。
发生冲突时以前面的v0.3为准：包括允许的风格化、未知部位处理、
新版九表情和物种适配动作。不要将旧主提示词与新模块同时注入。

# Cat & Dog Custom Sticker Prompt System

**Version:** v0.1  
**Status:** Prototype prompt baseline  
**Scope:** Cat + Dog only  
**Primary goal:** Identity consistency > cuteness > generation speed > cost  
**Output model:** two-stage generation: style preview sheet → selected-style 3×3 sticker sheet

> This document is the prompt source of truth for the local prototype stage. It intentionally does **not** define deployment, payment, account, database, or server architecture.

---

## 1. Product generation contract

### Stage 1 — Style Preview

Input: one original pet photo.  
Output: one **single large PNG** containing a **2×2 style preview sheet** of the same pet.

Four fixed style choices:

- **A — Soft Kawaii Chibi** (`soft_kawaii_chibi`)
- **B — Bold Cartoon Sticker** (`bold_cartoon_sticker`)
- **C — Cute Semi-Realistic** (`cute_semi_realistic`)
- **D — Storybook Watercolor** (`storybook_watercolor`)

Hard rules:

1. All four previews must depict the **same real pet** from the source photo.
2. Pose, viewing angle, crop, scale, and neutral cheerful expression must stay as similar as possible across A/B/C/D.
3. **STYLE is the only intended visual variable.**
4. Do not put A/B/C/D, style names, captions, watermarks, or any text inside the generated image.
5. The original uploaded pet photo remains the **identity source of truth**. A style preview is never allowed to replace the original photo as the sole identity reference for Stage 2.
6. Background must be **real alpha transparency**. A white background, checkerboard pattern drawn into the image, fake transparency, scene background, or near-white background is a failed output.

### Stage 2 — Final Sticker Sheet

Input:

- the same original pet photo;
- the style selected in Stage 1;
- one expression pack.

Output: one **single square PNG** containing a **3×3 grid / nine stickers**, intended to be programmatically cut into nine independent square sticker files later.

Hard rules:

1. Nine stickers must depict the **same pet**.
2. Identity must be derived from the original photo, not from a previously AI-generated preview alone.
3. Style must be consistent across all nine cells.
4. Each expression must be visually distinct.
5. Each cell must remain cut-safe: subject centered, comparable scale, no important anatomy crossing into neighboring cells.
6. The whole sheet must use **true transparent alpha** with no panel backgrounds.
7. No text in the image at this prototype stage.

---

## 2. Identity-locking rules

These rules are deliberately repeated in the prompts because identity drift is the highest-priority failure mode.

### 2.1 Cat identity anchors

Preserve, when visible in the reference photo:

- overall coat base color;
- exact major patch / stripe / point-color distribution;
- forehead markings and facial mask pattern;
- muzzle and chin color;
- white bib / white chest;
- white socks / glove markings and which paws have them;
- eye color and left/right symmetry or asymmetry;
- face width and muzzle proportion;
- ear size, ear angle, and ear tip shape;
- nose color;
- coat length and fluffiness;
- tail color pattern when visible;
- distinctive freckles, spots, scars, asymmetrical markings, or other identity cues.

Do **not** normalize the cat into a generic breed stereotype. A tuxedo cat must keep its actual white/black distribution; a tabby must keep recognizable stripe placement; a calico must keep its major color patches; a pointed cat must retain its real point pattern.

### 2.2 Dog identity anchors

Preserve, when visible in the reference photo:

- overall coat base color;
- exact major patch / mask / saddle distribution;
- eyebrow dots or facial points;
- muzzle length and width;
- muzzle color and blaze;
- eye color;
- ear type: upright / semi-upright / rose / folded / floppy;
- ear size and placement;
- nose size and color;
- forehead width and head silhouette;
- coat type: short / long / wiry / curly / fluffy / double coat;
- chest patch;
- white socks and which legs have them;
- tail shape, curl, plume, and color when visible;
- breed-defining proportions only insofar as they match the actual reference dog;
- distinctive asymmetrical markings.

Do **not** replace the dog with a generic breed icon. If breed is uncertain, preserve the visible individual rather than guessing a breed.

---

# PART A — CAT PROMPTS

## 3. Cat Stage 1 master prompt — 2×2 four-style preview sheet

Use this prompt when the model can generate all four style candidates in one image.

```text
Use the uploaded reference photo as the single identity source of truth for this real cat.

First, visually analyze and lock the cat’s identity before stylizing it. Preserve the same base coat color, major fur-pattern placement, forehead and facial markings, muzzle/chin color, eye color, face shape, ear size and angle, nose color, coat length, white bib/chest, white paws or glove markings, and any visible asymmetrical or distinctive markings. Do not simplify the cat into a generic breed stereotype. All four results must be immediately recognizable as the same individual cat from the reference photo.

Create ONE large PNG style-preview sheet with TRUE ALPHA TRANSPARENCY.

LAYOUT:
- exactly four isolated cat previews arranged as a clean 2×2 grid;
- top-left = Style A;
- top-right = Style B;
- bottom-left = Style C;
- bottom-right = Style D;
- equal visual scale in all four cells;
- same framing, same viewing angle, same body orientation, same cheerful-neutral expression, and as close as possible to the same pose in all four cells;
- each cat centered in its own quadrant with safe margins;
- no panel background, no box, no frame, no separator line.

STYLE A — SOFT KAWAII CHIBI:
2.5-head-tall chibi proportions, oversized rounded head, compact soft body, large but not identity-destroying eyes, rounded paws, gentle shapes, soft clean color blocks, highly adorable premium pet-sticker aesthetic. Preserve real fur markings rather than replacing them with generic cute patterns.

STYLE B — BOLD CARTOON STICKER:
thick smooth dark outline, expressive clean cartoon construction, strong readable silhouette, flat controlled colors, simplified but faithful fur pattern, crisp sticker-ready shapes, lively but not distorted facial features. Do not give the cat human fingers.

STYLE C — CUTE SEMI-REALISTIC:
retain the most faithful facial proportions, eye placement, ear geometry, muzzle, fur-color boundaries, and individual likeness while gently simplifying the cat into a polished cute digital illustration. Slightly enlarged expressive eyes are allowed, but the cat must still look unmistakably like the reference individual. No photorealistic rendering.

STYLE D — STORYBOOK WATERCOLOR:
warm premium children’s-book illustration feel, delicate watercolor-and-gouache texture contained inside the cat silhouette, soft hand-painted edges with enough contour clarity for a sticker, charming and artistic while preserving exact identity markings. Keep all paint texture on the subject only; the canvas behind the subject stays truly transparent.

TRANSPARENCY:
The canvas outside the four cat silhouettes must contain real alpha transparency. Do not draw a white background. Do not draw a gray or checkerboard transparency pattern. Do not create paper texture outside the subjects. Do not create environmental scenery, floor, shadow plate, halo rectangle, or colored cell background.

CONSISTENCY PRIORITY:
Identity consistency is more important than decorative detail. If a style would normally alter breed, coat pattern, face shape, eye color, or ear shape, preserve the real cat instead.

FORBIDDEN:
text, letters, numbers, labels A/B/C/D, watermark, logo, frame, border, panel backgrounds, scene background, extra animals, duplicated limbs, missing paws, human hands, human fingers, clothing, hats, random props, changed eye color, changed coat pattern, changed white-marking placement, different cats across cells, photorealism, 3D render.

FINAL CHECK:
The four previews must read as four art styles of ONE cat, not four similar cats.
```

---

## 4. Cat Style A — Soft Kawaii Chibi

```text
Transform the real cat in the reference photo into a premium Soft Kawaii Chibi pet sticker while preserving the cat’s identity with very high fidelity.

IDENTITY LOCK:
Preserve the exact base coat color, major stripe/patch distribution, forehead and facial markings, muzzle/chin color, eye color, face width, ear size and angle, nose color, coat length, white bib/chest, white glove/sock markings and their left/right placement, plus any asymmetrical identifying marks visible in the source photo. The result must look like this individual cat, not a generic cat of the same breed or color.

STYLE:
- 2.5-head-tall chibi proportions;
- oversized rounded head and compact body;
- large expressive round eyes, but keep original eye color and overall eye placement;
- rounded paws with simplified feline paw anatomy;
- soft, clean, polished color blocks;
- gentle curves and highly adorable expression;
- premium kawaii sticker aesthetic;
- minimal fur-detail lines only where useful;
- preserve recognizable fur markings as stable graphic shapes.

COMPOSITION:
Single cat, centered, isolated, clear silhouette, half-body or full-body depending on the source, with enough transparent margin for sticker cutting.

BACKGROUND:
TRUE transparent alpha only. No white background, no checkerboard pattern, no scene, no floor, no paper texture, no rectangular panel, no cast-shadow plate.

FORBIDDEN:
identity drift, different coat pattern, different eye color, different ear shape, extra cat, text, watermark, human fingers, clothing, props, photorealism, 3D render, overly detailed individual fur strands.
```

---

## 5. Cat Style B — Bold Cartoon Sticker

```text
Create a Bold Cartoon Sticker version of the real cat in the reference photo while keeping the same individual identity unmistakable.

IDENTITY LOCK:
Preserve base coat color, exact major pattern placement, facial mask/forehead markings, muzzle and chin color, eye color, face shape, ear geometry, nose color, coat length, white bib, white paws and their exact distribution, and visible asymmetrical markings. Do not standardize the cat into a generic breed template.

STYLE:
- bold smooth dark outline with consistent stroke weight;
- strong readable silhouette at small messaging-sticker size;
- flat, clean, saturated but faithful color blocks;
- expressive cartoon facial design without changing identity;
- simplified fur texture, using only a few controlled lines;
- rounded feline paws, no human fingers;
- energetic, polished, high-clarity sticker aesthetic;
- suitable for WhatsApp / messaging-scale viewing.

COMPOSITION:
Single isolated cat, centered, balanced margins, no important feature near the canvas edge.

BACKGROUND:
TRUE alpha transparency outside the cat. No white fill, no faux-checkerboard transparency, no environment, no floor, no panel.

FORBIDDEN:
identity drift, breed substitution, altered markings, altered eye color, human hands, extra limbs, text, logo, watermark, props, clothing, photorealistic fur, 3D render, gradients that muddy the silhouette.
```

---

## 6. Cat Style C — Cute Semi-Realistic

```text
Create a Cute Semi-Realistic illustrated sticker of the real cat in the reference photo. Likeness is the primary objective.

IDENTITY LOCK:
Match the reference cat’s real face width, muzzle proportion, eye placement and color, ear size and angle, nose color, coat base color, exact major patch/stripe boundaries, forehead/facial markings, chin/muzzle color, white bib/chest, white socks/gloves, and other distinctive asymmetrical details. Preserve the individual first; stylize second.

STYLE:
- polished cute digital illustration;
- slightly simplified anatomy with natural feline structure;
- gentle controlled stylization, not extreme chibi;
- eyes may be subtly enlarged for warmth but must preserve color, spacing and identity;
- fur rendered as clean grouped masses with a few soft texture accents, not thousands of strands;
- soft facial modeling with clear sticker silhouette;
- warm, premium, emotionally appealing;
- more likeness-focused than Styles A or B;
- no photorealism.

COMPOSITION:
One cat only, centered, isolated, clean outer contour, sticker-safe margins.

BACKGROUND:
True alpha transparency. No white background, no backdrop, no furniture, no floor, no painted paper outside the cat.

FORBIDDEN:
generic breed replacement, face-shape drift, eye-color drift, marking drift, age drift, extra animals, human features, text, watermark, props, photorealistic photo look, 3D render.
```

---

## 7. Cat Style D — Storybook Watercolor

```text
Create a premium Storybook Watercolor sticker illustration of the real cat in the reference photo while preserving the cat’s identity precisely.

IDENTITY LOCK:
Keep the actual base coat color, recognizable major markings, facial pattern, muzzle/chin color, eye color, ear shape and angle, face proportion, nose color, coat length, white chest/bib, white paws, and distinctive asymmetrical marks. Watercolor texture must never obscure or redesign the identity markings.

STYLE:
- charming hand-painted children’s-book illustration;
- watercolor + light gouache feel;
- soft pigment variation inside the subject;
- selective fine ink or painted contour where needed for readability;
- warm, gentle, premium handmade feeling;
- expressive and cute but not babyish;
- maintain a clear sticker silhouette;
- preserve enough color separation to remain readable after downscaling.

COMPOSITION:
Single isolated cat, centered, balanced transparent margins.

BACKGROUND:
The entire area outside the cat must be genuine alpha transparency. Watercolor paper grain must NOT fill the background. No painted wash behind the cat, no vignette, no white rectangle, no checkerboard pattern.

FORBIDDEN:
background wash, paper background, identity drift, altered markings, extra cat, scene, furniture, text, signature, watermark, photorealism, 3D render.
```

---

## 8. Cat Stage 2 master prompt — final 3×3 sticker sheet

Replace `{{STYLE_BLOCK}}` with the selected Style A/B/C/D definition.

```text
Use the uploaded ORIGINAL cat photo as the identity source of truth.

Create ONE square PNG containing exactly NINE distinct stickers of the SAME real cat, arranged as a precise 3×3 grid suitable for later programmatic cutting into nine equal square images.

IDENTITY FIRST:
Before drawing expressions, lock the cat’s identity from the original photo. Preserve the same base coat color, exact major stripe/patch placement, facial and forehead markings, muzzle/chin color, eye color, face shape, ear size and angle, nose color, coat length, white bib/chest, white paws or glove markings and their left/right placement, and any distinctive asymmetrical marks. Every cell must depict the same individual cat. Do not allow identity drift between expressions.

SELECTED STYLE:
{{STYLE_BLOCK}}

GRID / CUT-SAFETY:
- one square master canvas;
- exactly 3 rows × 3 columns;
- nine equal invisible cells;
- no visible grid lines or cell backgrounds;
- one cat sticker centered in each cell;
- comparable head size and overall visual scale across all cells;
- keep ears, paws, tail, hearts, tears, stars, and motion marks safely inside their own cell;
- no overlap across cell boundaries;
- no important detail touching the outer canvas edge;
- spacing must support clean equal-size programmatic cutting.

GLOBAL CHARACTER CONSISTENCY:
- same cat identity in every cell;
- same art style in every cell;
- same coat pattern geometry and colors;
- same eye color;
- same ear shape;
- same face proportion;
- same outline / rendering language;
- expression and pose may change, identity may not.

EXPRESSIONS — left to right, top to bottom:

1. HELLO / WAVE
Raise one front paw in a friendly feline waving gesture. Eyes curve into a cheerful smile, mouth open in a happy expression, subtle pink cheek blush allowed. Keep the paw anatomically paw-like; do not create human fingers.

2. APPROVAL / LIKE
Show a clear enthusiastic approval gesture using one raised paw and proud, pleased facial expression. Suggest the visual meaning of “thumbs up” without turning the paw into a human hand or adding human fingers. Confident upward mouth curve.

3. THANK YOU
Both front paws brought together politely in front of the chest, eyes closed in a warm grateful expression. One small heart above the head is allowed, fully contained within the cell.

4. ANGRY / PUFFED
Fur and tail visibly puffed, tense compact posture, narrowed or vertical pupils where stylistically appropriate, furrowed brow, small angry mouth. Up to three simple red anger marks allowed. Still cute, not violent or frightening.

5. SAD / CRYING
Large expressive eyes with two clear tear streams, downturned mouth, small paws near the eyes as if wiping tears. Subtle trembling motion marks allowed. Do not distort the face identity.

6. EXCITED / JUMPING
Body lifted in a joyful jump, both front paws raised, delighted open-mouth smile, bright excited eyes. Up to three small star accents allowed and must remain inside the cell.

7. SPEECHLESS / EYE ROLL
Eyes rolled upward showing a clear “speechless” emotion, mouth a short flat line, unimpressed posture. A few simple sweat / awkward marks allowed, but no text or punctuation characters.

8. SLEEPING
Cat curled naturally into a compact sleeping pose, eyes fully closed, peaceful facial expression, tail wrapped naturally if visible. Do NOT include letter “Z” or any written sleep symbol because the full sheet must remain text-free.

9. HUG / CUDDLE REQUEST
Both front paws extended forward in an inviting cuddle gesture, wide gentle watery eyes, tiny open mouth, affectionate pleading expression. Up to two small pink hearts allowed above the head, fully contained in the cell.

TRUE TRANSPARENCY:
The entire canvas outside every sticker subject and allowed decorative accent must be genuine alpha transparency. Do not create white cell backgrounds. Do not draw a checkerboard transparency pattern. Do not add scene backgrounds, colored circles, floor shadows, rectangular cards, paper texture, gradients behind the subjects, or any opaque sheet background.

NO TEXT:
No words, letters, numbers, punctuation, labels, captions, signatures, logos, watermarks, or “Z” symbols anywhere in the image.

NEGATIVE / FAILURE CONDITIONS:
- different-looking cats across cells;
- changed coat pattern or white-mark placement;
- changed eye color;
- changed ear geometry;
- changed breed appearance;
- accidental extra cat;
- duplicated or missing limbs;
- human hands or human fingers;
- anatomically impossible paw shapes;
- expression repetition;
- inconsistent scale;
- cell overlap;
- text of any kind;
- white or colored background;
- fake checkerboard transparency;
- photorealistic rendering;
- 3D render;
- excessive detailed fur that destroys sticker clarity;
- extra props unrelated to the expression.

QUALITY ORDER:
1. same-cat identity consistency;
2. expression clarity;
3. cut-safe 3×3 layout;
4. cuteness and polish;
5. decorative detail.

FINAL SELF-CHECK:
This must look like nine expressions performed by ONE recognizable cat character derived from the original pet photo, not nine loosely similar cats.
```

---

# PART B — DOG PROMPTS

## 9. Dog Stage 1 master prompt — 2×2 four-style preview sheet

```text
Use the uploaded reference photo as the single identity source of truth for this real dog.

First, visually analyze and lock the dog’s identity before stylizing it. Preserve the actual base coat color, major patch/mask/saddle distribution, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, forehead width, ear type and exact placement, nose size and color, coat length/texture, chest patch, white socks and which legs have them, visible tail shape, and any asymmetrical or distinctive markings. If breed is uncertain, preserve the visible individual rather than inventing a breed. All four results must be immediately recognizable as the same dog.

Create ONE large PNG style-preview sheet with TRUE ALPHA TRANSPARENCY.

LAYOUT:
- exactly four isolated dog previews arranged as a clean 2×2 grid;
- top-left = Style A;
- top-right = Style B;
- bottom-left = Style C;
- bottom-right = Style D;
- equal visual scale in all four cells;
- same framing, same viewing angle, same body orientation, same cheerful-neutral expression, and as close as possible to the same pose in all four cells;
- each dog centered in its own quadrant with safe margins;
- no panel background, no box, no frame, no separator line.

STYLE A — SOFT KAWAII CHIBI:
2.5-head-tall chibi proportions, oversized rounded head, compact soft body, expressive eyes, rounded paws, cute simplified silhouette, gentle clean colors, premium adorable sticker aesthetic. Preserve breed-defining muzzle, ears, coat type, and real markings.

STYLE B — BOLD CARTOON STICKER:
thick smooth dark outline, strong readable silhouette, flat controlled colors, expressive cartoon construction, clean sticker-ready shape. Keep the dog’s real ear type, muzzle geometry, head shape, and identifying coat pattern. Do not give the dog human hands or fingers.

STYLE C — CUTE SEMI-REALISTIC:
prioritize faithful likeness: real head shape, muzzle length, ear geometry, eye placement, coat pattern and breed feel, gently simplified into a polished cute digital illustration. No photorealism.

STYLE D — STORYBOOK WATERCOLOR:
warm premium children’s-book illustration feel, watercolor-and-gouache texture contained inside the dog silhouette, soft artistic rendering while preserving the exact dog identity and readable sticker contour. Keep the canvas behind the dog truly transparent.

TRANSPARENCY:
The canvas outside the four dog silhouettes must contain real alpha transparency. Do not draw a white background. Do not draw a gray or checkerboard transparency pattern. Do not create paper texture outside the subjects. Do not create scenery, floor, shadow plate, halo rectangle, or colored cell background.

CONSISTENCY PRIORITY:
Identity consistency is more important than decorative detail. If a style would normally alter breed, muzzle length, ear shape, coat pattern, face proportions, or eye color, preserve the real dog instead.

FORBIDDEN:
text, letters, numbers, labels A/B/C/D, watermark, logo, frame, border, panel backgrounds, scene background, extra animals, duplicated limbs, missing paws, human hands, human fingers, clothing, hats, random props, changed eye color, changed coat pattern, changed ear type, changed muzzle length, different dogs across cells, photorealism, 3D render.

FINAL CHECK:
The four previews must read as four art styles of ONE dog, not four dogs of a similar breed.
```

---

## 10. Dog Style A — Soft Kawaii Chibi

```text
Transform the real dog in the reference photo into a premium Soft Kawaii Chibi pet sticker while preserving individual identity with very high fidelity.

IDENTITY LOCK:
Preserve exact base coat color, major mask/patch/saddle distribution, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, head shape, ear type/size/placement, nose size and color, coat length and texture, chest patch, white socks and their leg placement, tail shape when visible, and any asymmetrical identifying marks. Do not turn the dog into a generic breed mascot.

STYLE:
- 2.5-head-tall chibi proportions;
- oversized rounded head with compact body;
- expressive larger eyes while preserving eye color and placement;
- soft rounded paws with canine anatomy;
- gentle, clean, premium color blocks;
- highly adorable but still recognizably the same dog;
- breed-defining muzzle and ear structure must remain visible;
- minimal fur-detail lines;
- stable graphic rendering of real coat markings.

COMPOSITION:
Single dog, centered, isolated, half-body or full-body depending on reference, transparent sticker-safe margin.

BACKGROUND:
TRUE transparent alpha only. No white background, no checkerboard, no environment, no floor, no panel, no paper texture.

FORBIDDEN:
identity drift, breed drift, shortened/lengthened muzzle that changes identity, changed ears, changed coat pattern, changed eye color, extra dog, text, watermark, human fingers, clothing, random props, photorealism, 3D render.
```

---

## 11. Dog Style B — Bold Cartoon Sticker

```text
Create a Bold Cartoon Sticker version of the real dog in the reference photo while keeping the same individual dog unmistakable.

IDENTITY LOCK:
Preserve base coat color, actual mask/patch/saddle geometry, facial blaze, eyebrow points, muzzle length and width, eye color, head shape, ear type and placement, nose size/color, coat type, chest patch, white socks, tail characteristics, and visible asymmetrical markings. Do not replace the dog with a generic breed caricature.

STYLE:
- thick smooth dark outline with consistent stroke weight;
- strong silhouette that remains readable at messaging-sticker size;
- flat clean colors faithful to the real dog;
- expressive cartoon face without changing muzzle/head identity;
- simplified coat texture;
- clear canine paws, no human fingers;
- energetic, polished, sticker-ready design;
- preserve breed feel and individual facial geometry.

COMPOSITION:
One dog only, centered, balanced transparent margins, no feature touching the canvas edge.

BACKGROUND:
Genuine alpha transparency outside the dog. No white fill, no fake checkerboard, no environment, no floor, no panel.

FORBIDDEN:
breed substitution, muzzle drift, ear drift, coat-pattern drift, human hands, extra limbs, text, logo, watermark, props, clothes, photorealistic fur, 3D render.
```

---

## 12. Dog Style C — Cute Semi-Realistic

```text
Create a Cute Semi-Realistic illustrated sticker of the real dog in the reference photo. Individual likeness is the primary objective.

IDENTITY LOCK:
Match the real head silhouette, forehead width, muzzle length/width, eye placement and color, ear type/size/placement, nose size/color, base coat color, facial mask or blaze, major body markings, eyebrow points, chest patch, white socks, coat length/texture, and distinctive asymmetry. If breed is uncertain, do not guess; follow the visible dog.

STYLE:
- polished cute digital illustration;
- natural canine anatomy with gentle simplification;
- restrained stylization, not extreme chibi;
- eyes may be subtly enlarged for warmth but must preserve identity;
- coat rendered as grouped soft masses with limited texture accents;
- breed feel remains recognizable;
- clean sticker silhouette;
- premium emotional portrait quality;
- no photorealism.

COMPOSITION:
One dog only, centered, isolated, clean contour, sticker-safe transparent margins.

BACKGROUND:
True alpha transparency. No white background, no furniture, no scenery, no floor, no paper field behind the dog.

FORBIDDEN:
generic breed replacement, head-shape drift, muzzle drift, ear drift, eye-color drift, marking drift, age drift, extra animals, human features, text, watermark, props, photorealistic photo look, 3D render.
```

---

## 13. Dog Style D — Storybook Watercolor

```text
Create a premium Storybook Watercolor sticker illustration of the real dog in the reference photo while preserving the dog’s identity precisely.

IDENTITY LOCK:
Keep the real base coat color, exact major markings, face mask/blaze, eyebrow points, eye color, ear type and placement, muzzle geometry, head proportion, nose color, coat type, chest patch, white socks, and distinctive asymmetrical marks. Watercolor texture must never redesign the dog’s breed feel or individual identity.

STYLE:
- warm hand-painted children’s-book illustration;
- watercolor + light gouache feel;
- soft pigment variation only within the dog silhouette;
- selective fine contour for sticker readability;
- premium handmade warmth;
- expressive and cute without turning the dog into a generic puppy icon;
- preserve small-size readability and strong outer silhouette.

COMPOSITION:
Single isolated dog, centered, balanced transparent margin.

BACKGROUND:
The whole area outside the dog must be real alpha transparency. Do not fill the canvas with watercolor paper grain. No wash, vignette, white rectangle, checkerboard, or scene behind the subject.

FORBIDDEN:
background wash, paper background, identity drift, breed drift, changed muzzle/ears/markings, extra dog, scenery, text, signature, watermark, photorealism, 3D render.
```

---

## 14. Dog Stage 2 master prompt — final 3×3 sticker sheet

Replace `{{STYLE_BLOCK}}` with the selected Style A/B/C/D definition.

```text
Use the uploaded ORIGINAL dog photo as the identity source of truth.

Create ONE square PNG containing exactly NINE distinct stickers of the SAME real dog, arranged as a precise 3×3 grid suitable for later programmatic cutting into nine equal square images.

IDENTITY FIRST:
Before drawing expressions, lock the dog’s identity from the original photo. Preserve the same base coat color, exact major patch/mask/saddle placement, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, head shape, ear type/size/placement, nose size and color, coat length/texture, chest patch, white socks and which legs have them, visible tail shape, and any distinctive asymmetrical markings. If breed is uncertain, follow the visible individual instead of inventing a breed. Every cell must depict the same dog.

SELECTED STYLE:
{{STYLE_BLOCK}}

GRID / CUT-SAFETY:
- one square master canvas;
- exactly 3 rows × 3 columns;
- nine equal invisible cells;
- no visible grid lines or cell backgrounds;
- one dog sticker centered in each cell;
- comparable head size and overall visual scale across all cells;
- keep ears, paws, tail, hearts, tears, stars, and motion marks safely inside their own cell;
- no overlap across cell boundaries;
- no important detail touching the outer canvas edge;
- spacing must support clean equal-size programmatic cutting.

GLOBAL CHARACTER CONSISTENCY:
- same dog identity in every cell;
- same art style in every cell;
- same muzzle length and head geometry;
- same ear type and placement;
- same coat pattern and colors;
- same eye color;
- same coat texture language;
- expression and pose may change, identity may not.

EXPRESSIONS — left to right, top to bottom:

1. HELLO / WAVE
Raise one front paw in a friendly canine waving gesture, cheerful eyes and happy open-mouth expression. Keep the paw canine; no human fingers.

2. APPROVAL / LIKE
Show a clear enthusiastic approval gesture with one raised front paw and a proud pleased face. Communicate the meaning of “thumbs up” through pose and expression without turning the paw into a human hand.

3. THANK YOU
Both front paws brought together politely in front of the chest, warm grateful expression, eyes gently closed or softened. One small heart allowed above the head, inside the cell.

4. ANGRY / GRUMPY
Clear grumpy emotion using ears, brows, eyes, mouth and body tension appropriate to this dog’s natural ear type. Keep it cute and non-threatening. Do not force upright ears on a floppy-eared dog. Up to three small anger marks allowed.

5. SAD / CRYING
Large expressive watery eyes, clear tears, downturned mouth, lowered or softened ears as appropriate to the actual ear anatomy, small paw near face if natural. Preserve muzzle and face identity.

6. EXCITED / JUMPING
Joyful jump with both front paws raised, excited open-mouth smile; tongue may appear only if natural and not identity-distorting. Up to three small star accents allowed, contained within the cell.

7. SPEECHLESS / EYE ROLL
Clear unimpressed / speechless expression, upward eye roll or sideways skeptical look, simple flat mouth. Ear position should remain anatomically consistent with the real dog. A few simple awkward/sweat marks allowed, but no text.

8. SLEEPING
Dog curled or lying naturally in a peaceful sleeping pose, eyes fully closed, relaxed ears and paws, tail resting naturally if visible. No letter “Z” or written sleep symbol.

9. HUG / CUDDLE REQUEST
Both front paws extended forward in an inviting cuddle gesture, soft pleading eyes, affectionate expression, slightly open mouth if appropriate. Up to two small pink hearts allowed, fully inside the cell.

TRUE TRANSPARENCY:
The entire canvas outside every sticker subject and allowed decorative accent must be genuine alpha transparency. No white cell backgrounds, no checkerboard transparency pattern, no environmental scene, no colored circles, no floor shadows, no rectangular cards, no paper texture, no opaque master-sheet background.

NO TEXT:
No words, letters, numbers, punctuation, labels, captions, signatures, logos, watermarks, or “Z” symbols anywhere.

NEGATIVE / FAILURE CONDITIONS:
- different dogs across cells;
- breed drift;
- changed muzzle length or width;
- changed ear type;
- changed coat pattern or white-sock placement;
- changed eye color;
- accidental extra dog;
- duplicated or missing limbs;
- human hands or fingers;
- expression repetition;
- inconsistent scale;
- cell overlap;
- text;
- white or colored background;
- fake checkerboard transparency;
- photorealistic render;
- 3D render;
- excessive fur detail that destroys sticker readability;
- unrelated props.

QUALITY ORDER:
1. same-dog identity consistency;
2. expression clarity;
3. cut-safe 3×3 layout;
4. cuteness and polish;
5. decorative detail.

FINAL SELF-CHECK:
This must look like nine expressions performed by ONE recognizable dog character derived from the original pet photo, not nine dogs from the same breed.
```

---

# PART C — STYLE BLOCKS FOR STAGE 2 INJECTION

These compact blocks are intended to be injected into the Stage 2 master prompt after the user selects A/B/C/D.

## 15. Style A block — `soft_kawaii_chibi`

```text
SOFT KAWAII CHIBI: 2.5-head-tall proportions, oversized rounded head, compact soft body, expressive large eyes without changing eye color or identity, rounded species-correct paws, gentle clean color blocks, minimal fur lines, highly adorable premium sticker aesthetic. Preserve all identity-defining markings exactly. No photorealism, no 3D.
```

## 16. Style B block — `bold_cartoon_sticker`

```text
BOLD CARTOON STICKER: thick smooth dark outline, consistent stroke weight, strong readable silhouette, clean flat colors, expressive cartoon construction, simplified fur texture, crisp sticker-ready shapes, high readability at small messaging size. Preserve exact identity markings and species anatomy. No human fingers, no photorealism, no 3D.
```

## 17. Style C block — `cute_semi_realistic`

```text
CUTE SEMI-REALISTIC: prioritize individual likeness, preserve real facial/head proportions, eye placement and color, ear geometry, muzzle structure, and exact coat-marking boundaries; gently simplify into a polished cute digital illustration with restrained stylization, subtle eye enlargement only if identity remains intact, grouped soft fur masses, clear sticker silhouette. No photorealistic photo look, no 3D.
```

## 18. Style D block — `storybook_watercolor`

```text
STORYBOOK WATERCOLOR: premium children’s-book watercolor + light gouache feel, pigment and paper-like texture contained only inside the subject silhouette, warm handmade character, soft but readable contour, preserved exact identity markings, clear sticker silhouette and small-size readability. The canvas outside the subject remains true alpha transparency; no background wash, no paper field, no 3D.
```

---

# PART D — PROTOTYPE TEST PROTOCOL

## 19. Recommended test order

To avoid confusing model problems with prompt problems, change only one variable at a time.

1. Test **Cat Stage 1 master prompt** with 5–10 visually different cats.
2. Check whether A/B/C/D are visibly different while still being the same cat.
3. Select one style and run **Cat Stage 2**.
4. Repeat the same cat with all four styles only after identity consistency is acceptable.
5. Then test **Dog Stage 1** with dogs covering at least:
   - upright ears;
   - floppy ears;
   - short muzzle;
   - long muzzle;
   - short coat;
   - long / curly coat;
   - high-contrast markings.
6. Then test **Dog Stage 2**.

## 20. Failure labels

Use these labels when recording prototype results:

- `IDENTITY_DRIFT` — no longer clearly the same individual pet.
- `MARKING_DRIFT` — key coat markings moved, disappeared, or changed.
- `EYE_DRIFT` — eye color / placement changed materially.
- `EAR_DRIFT` — ear type or geometry changed materially.
- `MUZZLE_DRIFT` — dog muzzle changed enough to alter identity.
- `STYLE_COLLAPSE` — A/B/C/D look too similar.
- `STYLE_OVERPOWERED_IDENTITY` — style changed identity-defining features.
- `GRID_LEAK` — limbs / decorations cross into neighboring cells.
- `SCALE_DRIFT` — character size varies too much across cells.
- `EXPRESSION_COLLAPSE` — several expressions look effectively the same.
- `FAKE_TRANSPARENCY` — white / checkerboard / opaque background instead of alpha.
- `TEXT_LEAK` — model generated letters, labels, numbers, or symbols.
- `ANATOMY_ERROR` — duplicated/missing limbs or human fingers.

## 21. Prototype acceptance priorities

Evaluate outputs in this order:

1. **Identity consistency** — must still be the same pet.
2. **Cuteness / willingness to buy** — should feel emotionally appealing.
3. **Sticker readability** — must still work when reduced to chat-sticker size.
4. **Layout / cut safety** — later processing must be reliable.
5. **Transparency correctness** — real alpha, not fake transparency.
6. **Speed and generation cost** — optimize only after the above are acceptable.

---

# 22. Prompt inventory

This document contains:

- 4 cat style-specific prompts;
- 4 dog style-specific prompts;
- 1 cat 2×2 four-style preview master prompt;
- 1 dog 2×2 four-style preview master prompt;
- 1 cat final 3×3 master prompt;
- 1 dog final 3×3 master prompt;
- 4 compact reusable Stage-2 style blocks.

The core “4 + 4” style prompts are the eight species/style variants. The master prompts are included so the prototype can be tested directly without manually assembling prompt fragments.

---

## 23. Non-goals for this version

Not defined in this prompt baseline:

- baby / human sticker generation;
- dynamic GIF stickers;
- user-defined expression packs;
- 18 / 27 expression pack contents;
- server deployment;
- payment pricing;
- account reuse;
- order workflow;
- WeChat / WhatsApp final export dimensions;
- model/API vendor choice.

Those should be frozen separately after image-generation quality is validated.

