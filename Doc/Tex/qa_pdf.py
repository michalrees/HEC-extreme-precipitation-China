from pathlib import Path
from pypdf import PdfReader
from PIL import Image, ImageDraw
p=Path('Doc/Tex')
qa=p/'qa'
doc=PdfReader(p/'manuscript.pdf')
for i,page in enumerate(doc.pages):
    txt=page.extract_text()
    print(i+1, 'chars',len(txt),txt[:75].replace('\n',' '))
files=sorted(qa.glob('page-*.png'))
for start in range(0,len(files),15):
    sheet=Image.new('RGB',(1500,1260),'#dddddd')
    for j,f in enumerate(files[start:start+15]):
        im=Image.open(f).convert('RGB'); im.thumbnail((290,392))
        x=(j%5)*300;y=(j//5)*420
        sheet.paste(im,(x+(300-im.width)//2,y+22))
        ImageDraw.Draw(sheet).text((x+8,y+5),f.stem,fill='black')
    sheet.save(qa/f'contact-{start//15+1}.png')
