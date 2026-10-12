"""Rebuild the AGU draft from the supplied Markdown; requires Pandoc."""
from pathlib import Path
import re
import shutil
import subprocess
import json

OUT = Path(__file__).resolve().parent
DOC = OUT.parent
SRC = DOC / '涌现约束_v2.md'
ASSETS = Path('C:/Users/yuhao/.codex/skills/agu-manuscript/assets')
source = SRC.read_text(encoding='utf-8-sig')
# 只从 <cite>…</cite> 里取引文键：正文里还有作者邮箱（linhaozhong@ninhm.ac.cn），
# 直接对全文做 @([\w-]+) 会把 "ninhm" 当成引文键而误报缺失。
citations = sorted(set(re.findall(r'@([\w-]+)', ' '.join(re.findall(r'<cite>(.*?)</cite>', source, flags=re.S)))))
bib = (DOC / '参考文献.bib').read_text(encoding='utf-8-sig')
keys = re.findall(r'@\w+\s*\{\s*([^,]+),', bib)
missing = sorted(set(citations) - set(keys))
assert not missing, missing
shutil.copy2(ASSETS / 'agujournal2019.cls', OUT / 'agujournal2019.cls')
shutil.copy2(DOC / '参考文献.bib', OUT / 'references.bib')
(OUT / 'figures').mkdir(exist_ok=True)

def prep(s):
    s = re.sub(r'<cite>(.*?)</cite>', lambda m: '\\cite{' + ','.join(re.findall(r'@([\w-]+)', m[1])) + '}', s, flags=re.S)
    s = re.sub(r'https?://[^\s<>]+', lambda m: '\\url{' + m[0].rstrip('.') + '}' + ('.' if m[0].endswith('.') else ''), s)
    s = re.sub(r'图\s*(\d+)', lambda m: '图\u00a0\\ref{fig:' + m[1] + '}', s)
    s = re.sub(r'表\s*(\d+)', lambda m: '表\u00a0\\ref{tab:' + m[1] + '}', s)
    s = re.sub(r'式\s*\(([1-9])\)', lambda m: '式\u00a0\\eqref{eq:' + m[1] + '}', s)
    return s

def latex(s):
    p = subprocess.run(['pandoc', '-f', 'markdown+raw_tex+tex_math_dollars-subscript-superscript-smart-fancy_lists', '-t', 'latex', '--wrap=none'], input=prep(s), text=True, encoding='utf-8', capture_output=True, check=True)
    return p.stdout.strip()

figs = []
figure_blocks = {}
def figure(m):
    block = m[0]
    n = re.search(r'Fig\.(\d+)', block)[1]
    path = (DOC / re.search(r'src="([^"]+)"', block)[1]).resolve()
    assert path.exists(), path
    shutil.copy2(path, OUT / 'figures' / f'Fig{n}.jpg')
    caption = block.split('<figcaption>', 1)[1]
    caption = re.sub(r'</?(?:figcaption|figure)>', '', caption).strip()
    caption = re.sub(r'^Fig\.\d+\s*', '', caption)
    figs.append(int(n))
    chunks = []
    chunk = ''
    for sentence in re.split(r'(?<=。)', caption):
        if len(chunk) + len(sentence) > 520 and chunk:
            chunks.append(chunk)
            chunk = ''
        chunk += sentence
    if chunk:
        chunks.append(chunk)
    if len(chunks) > 2:
        chunks = [chunks[0], ''.join(chunks[1:])]
    if n == '6':
        chunks = [caption]
    floats = ['\n'.join([r'\begin{figure}[htbp]', r'\centering', rf'\includegraphics[width=\textwidth,height=0.58\textheight,keepaspectratio]{{figures/Fig{n}.jpg}}', '\\caption{' + latex(chunks[0]) + '}', rf'\label{{fig:{n}}}', r'\end{figure}'])]
    for chunk in chunks[1:]:
        floats.append('\n'.join([r'\begin{figure}[p]', r'\ContinuedFloat', '\\caption[]{（续）' + latex(chunk) + '}', r'\end{figure}']))
    token = 'AGUFIGUREPLACEHOLDER' + n + 'END'
    figure_blocks[token] = (r'\FloatBarrier' + '\n' if len(chunks) > 1 else '') + '\n\n'.join(floats) + ('\n' + r'\FloatBarrier' if len(chunks) > 1 else '')
    return '\n\n' + token + '\n\n'

text = re.sub(r'<figure>.*?</figure>', figure, source, flags=re.S)
def equation(m):
    body = m[1].strip()
    n = re.search(r'\\tag\{(\d+)\}', body)[1]
    body = re.sub(r'\\tag\{\d+\}', '', body).strip()
    return '\n\n' + '\n'.join([r'\begin{linenomath*}', r'\begin{equation}', body, rf'\label{{eq:{n}}}', r'\end{equation}', r'\end{linenomath*}']) + '\n\n'
text = re.sub(r'\$\$(.*?)\$\$', equation, text, flags=re.S)
table = r'''\begin{table}[htbp]
\caption{观测数据列表}
\label{tab:1}
\centering
\begin{tabular}{lll}
\hline
Dataset & Source & Resolution \\
\hline
CN05.1 & CMA & $0.25^\circ \times 0.25^\circ$ \\
HGCDC & TPDC & $0.1^\circ \times 0.1^\circ$ \\
CHM\_PRE V2 & TPDC & $0.1^\circ \times 0.1^\circ$ \\
CPC Global Unified Precipitation & NOAA & $0.5^\circ \times 0.5^\circ$ \\
\hline
\end{tabular}
\end{table}'''
text = re.sub(r'表1 观测数据列表\s*\n(?:\|[^\n]*\n)+', lambda m: table + '\n\n', text)
abstract = text.split('# Abstract', 1)[1].split('# Plain Language Summary', 1)[0].strip()
pls = text.split('# Plain Language Summary', 1)[1].split('# 1 Introduction', 1)[0].strip()
body = '# 1 Introduction' + text.split('# 1 Introduction', 1)[1]
body = body.split('# Reference', 1)[0]
# The declaration is emitted in the AGU back matter below.
body = body.split('# Conflict of Interest Disclosure', 1)[0]
body = re.sub(r'^# Data Availability Statement', r'\\section*{Open Research}\n\n\\subsection*{Data Availability Statement}', body, flags=re.M)
body = re.sub(r'^(#{1,2}) (\d+(?:\.\d+)?) (.+)$', lambda m: '\\' + ('section' if len(m[1]) == 1 else 'subsection') + '{' + m[3] + '}\n\\label{sec:' + m[2] + '}', body, flags=re.M)

preamble = r'''% !TeX program = xelatex
% Chinese working draft, based on the supplied AGU template.
\documentclass[draft]{agujournal2019}
\usepackage{fontspec}
\usepackage[UTF8,fontset=fandol,scheme=plain]{ctex}
\usepackage{amsmath,amssymb}
\usepackage{newunicodechar}
\usepackage{xurl}
\usepackage{lineno}
\usepackage{caption}
\captionsetup{font=small,skip=6pt}
\usepackage[section]{placeins}
% apacite in the supplied class is used without hyperref.

\newcommand{\pending}[1]{\textbf{[待补：#1]}}
\newunicodechar{σ}{\ensuremath{\sigma}}
\newunicodechar{ρ}{\ensuremath{\rho}}
\newunicodechar{Δ}{\ensuremath{\Delta}}
\newunicodechar{λ}{\ensuremath{\lambda}}
\newunicodechar{φ}{\ensuremath{\varphi}}
\newunicodechar{α}{\ensuremath{\alpha}}
\newunicodechar{β}{\ensuremath{\beta}}
\newunicodechar{√}{\ensuremath{\surd}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{−}{\ensuremath{-}}
\newunicodechar{×}{\ensuremath{\times}}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{∞}{\ensuremath{\infty}}
\newunicodechar{²}{\ensuremath{^{2}}}
\newunicodechar{₁}{\ensuremath{_{1}}}
\newunicodechar{₀}{\ensuremath{_{0}}}
\newunicodechar{◦}{\ensuremath{^{\circ}}}
\draftfalse
\linenumbers
\setlength{\emergencystretch}{2em}
\journalname{Target journal to be confirmed}
\begin{document}
\title{Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China}
\authors{Haoran Yu\affil{1}, Linhao Zhong\affil{1}, Zhaohui Gong\affil{1}}
\affiliation{1}{National Institute of Natural Hazards, Ministry of Emergency Management of China, Beijing, 100085}
\correspondingauthor{Linhao Zhong}{linhaozhong@ninhm.ac.cn}
\begin{keypoints}
\item 分层涌现约束显式整合观测与模式不确定性以约束中国未来极端降水强度
\item 历史降水变率约束使各区域未来极端降水强度的模式间标准差平均缩减百分之十六至二十七
\item 约束关系对模式成员剔除保持稳健且调整场具有明显的区域与尺度差异
\end{keypoints}
'''
tail = r'''
\section*{Conflict of Interest Disclosure}
The authors declare no conflicts of interest.
\acknowledgments
This work was supported by the National Natural Science Foundation of China under the project ``Mechanisms of Atmospheric Water Cycle Anomalies in Major River Basins of China under Global Change'' (Grant No. U2342210).
\clearpage
\bibliography{references}
\end{document}
'''
result = preamble + '\n\\begin{abstract}\n' + latex(abstract) + '\n\\end{abstract}\n\n\\section*{Plain Language Summary}\n' + latex(pls) + '\n\n' + latex(body) + '\n' + tail
for token, block in figure_blocks.items():
    result = result.replace(token, block.replace(r'\cite{', r'\protect\cite{'))
(OUT / 'manuscript.tex').write_text(result, encoding='utf-8')
(OUT / 'conversion-audit.json').write_text(json.dumps({'source': str(SRC), 'figures': figs, 'equations': len(re.findall(r'\\tag\{\d+\}', source)), 'tables': 1, 'cited_keys': citations, 'missing_citations': missing, 'bibliography_entries': len(keys)}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'figures': len(figs), 'cited_keys': len(citations), 'missing': missing, 'tex_characters': len(result)}))




