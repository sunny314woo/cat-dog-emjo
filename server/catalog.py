from pathlib import Path
import json

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'config/catalog.json').read_text())
EXPRESSIONS = CATALOG['theme']['expressions']
STYLES = {s['id']: s for s in CATALOG['styles']}
PRODUCTS = {p['id']: p for p in CATALOG['products']}
PACK_PROMPT_VERSION = 'v0.9-human-silhouette'

def build_style_prompt(style_ids, reference_count):
    if len(style_ids)!=4 or len(set(style_ids))!=4 or any(s not in STYLES or not STYLES[s]['active'] for s in style_ids):
        raise ValueError('需要四种已开放的风格')
    if reference_count not in (1,2,3):raise ValueError('需要 1–3 张照片')
    lines=['根据原照片中的同一个指定主体，生成一张正方形2×2四风格预览母图。',
           '第一张照片是身份主参考，其余照片只补充同一主体特征。保留脸型、花纹、发型或耳型及原有穿戴。',
           '四格保持同一个自然姿势、视角和构图；按原照片可见范围选择头部、半身或全身，不强补未展示的下半身。可见头发、耳朵、手部或尾巴必须完整，每格只有一个主体。',
           '人物按原有年龄感画出自然脸型、发际线和五官关系，保留服装款式与花纹，不套用统一宝宝脸。半身像的衣服底部需自然收成独立贴纸轮廓，四周可见留白，不把衣服横切在格子边缘。',
           '按从左到右、从上到下顺序分别采用以下四种风格，不混合画风：']
    for i,sid in enumerate(style_ids):lines.append(f'{i+1}. '+STYLES[sid]['prompt'])
    lines.extend(['每个主体完整位于自己格子中央70%范围，四周留白，禁止主体或配饰跨格。',
                  '纯白背景，不要格线、阴影、棋盘格、文字、编号、水印和额外道具。'])
    return '\n'.join(lines)

def build_prompt(style_id: str, reference_count: int, accessories: bool, style_reference=False) -> str:
    """Captions/display labels NEVER enter model inputs. Order is the reveal contract."""
    if style_id not in STYLES or not STYLES[style_id]['active']:
        raise ValueError('请选择已开放的风格')
    if reference_count not in (1, 2, 3): raise ValueError('需要 1–3 张照片')
    lines = ['根据参考照片绘制同一个指定主体的一张正方形3×3九宫格表情母图。',
             '自行识别可见主体是人物还是动物及其年龄感或物种结构，不需要用户指定类别。',
             '第一张为身份主参考，其余照片仅补充同一主体的可见特征，不合成人或动物；原照片不锁定九格的姿势、视角或轮廓。',
             '保留脸型、眼位、发型或耳型、口鼻或喙、颜色花纹和已有配件；不推断不可见身份信息。',
             '每格仅一个相同主体。合照只处理第一张框选范围内的唯一主体；主体不清时不得混合。',
             '身份一致只锁定脸型、年龄、毛色花纹和原有穿戴，不等于九格同一张正面证件照。',
             '人物分支：先在内部确认原照片的脸颊轮廓、发际线与发型、眼鼻口相对位置、服装款式和花纹，再用这些特征画同一个人；不要将真人五官贴到九个相同躯干上，不把儿童成人化或成人幼儿化。',
             '人物情绪由眉毛、双眼、嘴形、头颈姿态和肩臂动作共同表达；在保持相似度的前提下增强反应幅度。高兴可舒展、委屈可收拢、生气可挺直、困倦可松弛，不能只移动嘴角。手势保持自然解剖，不用复杂交叠手指，不出现多余肢体。动物分支仍按物种结构表达，不套用人的手臂。',
             '四风格预览的同姿势、同角度规则只属于第一阶段，本张九宫格不得沿用。',
             '每格必须有清楚的主动作，并在眉眼嘴形、头部视角、身体轮廓中至少两项与其他格明显区分；遮住文案仍应能区分九种反应。',
             '动作幅度鲜明、自然、符合物种与年龄；通过肢体舒展、收拢、身体倾斜与转向变化，不以放大到触边制造大动作。原照不可见的身体不强补，只有头部时加强头姿和眉眼差异。',
             '本页没有单眼眨眼表情。双眼可见时必须同时睁开、协调眯起或同时闭合；禁止无意的一眼睁一眼闭。侧向透视自然遮住一只眼不等于眨眼，不强求透视下两眼同样大。',
             '风格：' + STYLES[style_id]['prompt'].replace('Q版比例变化不改变四风格阶段指定姿势与角度。', ''),
             '九格顺序从左到右、从上到下，情绪不能随机替换；动作按物种和年龄自然适配：']
    for expression in EXPRESSIONS:
        line = f"{expression['cell_index']}. {expression['semantic']}"
        line += '；视角与轮廓：' + expression['pose'] + '；眼睛：' + expression['eyes']
        if accessories and expression['accessory']:
            line += '；允许的小配饰：' + expression['accessory']
        lines.append(line)
    lines.extend(['九宫格使用3×3等大逻辑区域，每个主体连同耳朵、尾巴、配饰完全放在本区域中央72%宽高内，四周各留14%空白。主体和配饰不得触及边界，不绘制格线；不靠换配饰重复情绪。最终512×512是程序排版交付尺寸，不是要求模型逐像素定位。',
                  '半身人物的衣服下沿在区域内部自然收成连续完整的贴纸轮廓，底部仍有留白；不画成沿整格下边缘齐切的矩形肖像。白色衣料、花纹、袖口和浅色配件属于不透明前景，不能当作背景留洞，不能让衣服融入背景。',
                  '无文字、字母、数字、标点、标志、水印；不把未提供的贴纸文案解释为物种或道具。',
                  '仅保留指定小配饰和少量情绪装饰，不遮挡脸部，不增加其他主体、场景、地面投影。',
                  '背景为整页一致、均匀无纹理的纯色，并与主体外缘的衣物和毛发颜色明显区分，或输出真实透明；禁止九块独立奶油色纸卡、米白色底板、渐变、背景纸纹和棋盘格。纸张与蜡笔颗粒仅在主体内部，不在白衣周围加白色矩形。'])
    if not accessories: lines.append('不新增小道具或穿戴；保留原照片可见配件和少量情绪线。')
    if style_reference:
        lines.append(f'前{reference_count}张是原照片，负责锁定身份。最后第{reference_count+1}张是用户选中的单一风格参考，只沿用其线条、色彩、比例处理和材质；其姿势、角度和表情不作为九格模板，不混入其他风格。身份有冲突时以原照片为准。')
    return '\n'.join(lines)
