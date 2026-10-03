"""Sync public style definitions from the maintained prompt library (no demo HTML)."""
from pathlib import Path
import json
import re
ROOT = Path(__file__).resolve().parents[1]
s = (ROOT / 'PET_STICKER_PROMPTS.md').read_text()
styles = []
for letter, name, key, prompt in re.findall(r'### ([A-M]) — (.*?)\s*— ([a-z_0-9]+)\n```text\n(.*?)\n```', s, re.S):
    styles.append(dict(id=key, letter=letter, name=name.split(' / ')[-1], prompt=prompt,
                       active=letter in 'ABCD', sample_quadrant='ABCD'.find(letter)))
assert len(styles) == 13
rows = [
 ('hello','打招呼','来啦','👋','友好微笑，轻抬可见的手、前爪或单翼致意',''),
 ('yes','赞同','收到','👌','满意点头，精神饱满，不重复挥手',''),
 ('thanks','感谢','谢谢你','🌷','温柔眼神，轻低头致意，不强迫合十','一朵小花放在身旁'),
 ('angry','生气','哼','💢','皱眉、口部紧绷、身体紧凑，保持物种和年龄结构',''),
 ('sad','难过','委屈巴巴','💧','低头、委屈眼神、少量泪滴，不扭曲口鼻',''),
 ('excited','兴奋','冲鸭','✨','眼睛明亮，开心张嘴，可见肢体轻抬欢呼，半身用身体上扬表达','无字的小旗，放在身旁或自然持握'),
 ('speechless','无语','已读','🙃','轻侧目、半闭眼、平静嘴形，保持眼部结构',''),
 ('sleep','睡觉','晚安','☾','闭眼休息，头轻靠手、前爪或自然收拢，鳥类保持翼与喙结构','一顶小睡帽，不遮住关键脸部特征'),
 ('love','爱意','贴贴','♡','柔和眼神、轻歪头，一至两个小爱心，不使用泪滴','')
]
expressions = [dict(id=i,cell_index=n+1,emotion=e,label=l,icon=icon,semantic=sem,accessory=acc)
               for n,(i,e,l,icon,sem,acc) in enumerate(rows)]
products = [dict(id=k,name=n,packs=c,usd_minor=p) for k,n,c,p in [
 ('FIRST_PACK_UNLOCK','解锁这一套',0,699),('PACK_1','再做一套',1,999),
 ('PACK_3','三次小惊喜',3,1999),('PACK_5','五次慢慢玩',5,2999)]]
(ROOT / 'config/catalog.json').write_text(json.dumps(dict(version='v2.4', styles=styles,
 theme=dict(id='everyday_a',name='日常小心情',description='九种常用心情，刚好够陪你聊一天。',expressions=expressions),
 products=products), ensure_ascii=False, indent=2)+'\n')
