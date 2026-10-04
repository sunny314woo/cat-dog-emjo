from pathlib import Path
import json

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'config/catalog.json').read_text())
EXPRESSIONS = CATALOG['theme']['expressions']
STYLES = {s['id']: s for s in CATALOG['styles']}
PRODUCTS = {p['id']: p for p in CATALOG['products']}

def build_style_prompt(style_ids, reference_count):
    if len(style_ids)!=4 or len(set(style_ids))!=4 or any(s not in STYLES or not STYLES[s]['active'] for s in style_ids):
        raise ValueError('需要四种已开放的风格')
    if reference_count not in (1,2,3):raise ValueError('需要 1–3 张照片')
    lines=['根据原照片中的同一个指定主体，生成一张正方形2×2四风格预览母图。',
           '第一张照片是身份主参考，其余照片只补充同一主体特征。保留脸型、花纹、发型或耳型及原有穿戴。',
           '四格保持同一个自然姿势、视角和构图，完整显示头部、身体及尾巴；每格只有一个主体。',
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
             '第一张为身份与构图主参考，其余照片仅补充同一主体的可见特征，不合成人或动物。',
             '保留脸型、眼位、发型或耳型、口鼻或喙、颜色花纹和已有配件；不推断不可见身份信息。',
             '每格仅一个相同主体。合照只处理第一张框选范围内的唯一主体；主体不清时不得混合。',
             '风格：' + STYLES[style_id]['prompt'].replace('Q版比例变化不改变四风格阶段指定姿势与角度。', ''),
             '九格顺序从左到右、从上到下，情绪不能随机替换；动作按物种和年龄自然适配：']
    for expression in EXPRESSIONS:
        line = f"{expression['cell_index']}. {expression['semantic']}"
        if accessories and expression['accessory']:
            line += '；允许的小配饰：' + expression['accessory']
        lines.append(line)
    lines.extend(['九宫格使用3×3等大逻辑区域，每个主体连同耳朵、尾巴、配饰完全放在本区域中央72%宽高内，四周各留14%空白。主体和配饰不得触及边界，不绘制格线；不靠换配饰重复情绪。最终512×512是程序排版交付尺寸，不是要求模型逐像素定位。',
                  '无文字、字母、数字、标点、标志、水印；不把未提供的贴纸文案解释为物种或道具。',
                  '仅保留指定小配饰和少量情绪装饰，不遮挡脸部，不增加其他主体、场景、地面投影。',
                  '背景使用干净单色或真实透明，不绘制棋盘格；纸张与蜡笔颗粒仅在主体内部。'])
    if not accessories: lines.append('不新增小道具或穿戴；保留原照片可见配件和少量情绪线。')
    if style_reference:
        lines.append(f'前{reference_count}张是原照片，负责锁定身份。最后第{reference_count+1}张是用户选中的单一风格参考，严格沿用其线条、色彩和材质；不复制其姿势，不混入其他风格。身份有冲突时以原照片为准。')
    return '\n'.join(lines)
