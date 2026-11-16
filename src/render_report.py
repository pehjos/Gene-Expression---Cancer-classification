"""Render every report page and a contact sheet for visual quality assurance."""
from pathlib import Path
import pymupdf
from PIL import Image, ImageOps, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'tmp/pdfs';folder.mkdir(parents=True,exist_ok=True)
doc=pymupdf.open(ROOT/'output/pdf/academic_report.pdf')
thumbs=[]
for i,page in enumerate(doc):
    output=folder/f'report_page_{i+1:02}.png'
    page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(output)
    with Image.open(output) as im:
        thumb=ImageOps.contain(im,(298,421)).convert('RGB')
        tile=Image.new('RGB',(320,452),'#dbe3e8');tile.paste(thumb,((320-thumb.width)//2,8))
        ImageDraw.Draw(tile).text((12,434),f'Page {i+1}',fill='black');thumbs.append(tile)
sheet=Image.new('RGB',(320*3,452*((len(thumbs)+2)//3)),'white')
for i,tile in enumerate(thumbs):sheet.paste(tile,((i%3)*320,(i//3)*452))
sheet.save(folder/'report_contact_sheet.png')
print(f'Rendered {len(doc)} pages to {folder}')
