from pathlib import Path
from collections import Counter
import re,json
p=Path('Doc/Tex'); src=(p.parent/'涌现约束_v2.md').read_text(encoding='utf-8-sig'); tex=(p/'manuscript.tex').read_text(encoding='utf-8')
a=Counter(re.findall(r'[\u4e00-\u9fff]',src));b=Counter(re.findall(r'[\u4e00-\u9fff]',tex))
print('Missing Chinese character counts:',dict(a-b))
s=Counter(re.findall(r'@([\w-]+)',src));t=Counter(k for group in re.findall(r'\\cite\{([^}]+)\}',tex) for k in group.split(','))
print('Citation occurrence differences:',dict(s-t),dict(t-s))
print('Labels',re.findall(r'\\label\{([^}]+)\}',tex))
print('Potential markup leftovers:',re.findall(r'AGUFIGUREPLACEHOLDER|<cite>|<figure>|textbackslash|textasciitilde',tex))
