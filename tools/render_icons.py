"""Render the approved D artwork from outline glyphs, not embedded bitmap strikes.

Uses installed MS Gothic without redistributing its font file. Runtime needs only
the generated PNG/ICO assets. Each native size is rendered separately at 8x.
"""
import argparse
import io
import struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

SIZES=(16,20,24,32,48,64,128,256,512)

def render(character,fill,size,font_path):
    scale=8
    n=size*scale
    im=Image.new('RGBA',(n,n),(0,0,0,0))
    draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((0,0,n-1,n-1),radius=size*.08*scale,
        fill=fill,outline='#111827',width=max(1,round(size/64))*scale)
    font=ImageFont.truetype(str(font_path),round(size*.82*scale))
    box=draw.textbbox((0,0),character,font=font)
    x=(n-(box[2]-box[0]))/2-box[0]
    y=(n-(box[3]-box[1]))/2-box[1]
    draw.text((round(x),round(y)),character,font=font,fill='#111827')
    return im.resize((size,size),Image.Resampling.LANCZOS)

def write_ico(images,path):
    sizes=[n for n in SIZES if n<=256]
    blobs=[]
    for n in sizes:
        out=io.BytesIO();images[n].save(out,format='PNG');blobs.append(out.getvalue())
    data=bytearray(struct.pack('<HHH',0,1,len(sizes)))
    offset=6+16*len(sizes)
    for n,blob in zip(sizes,blobs):
        data.extend(struct.pack('<BBBBHHII',0 if n==256 else n,0 if n==256 else n,0,0,1,32,len(blob),offset))
        offset+=len(blob)
    for blob in blobs:data.extend(blob)
    path.write_bytes(data)

def build(output,font_path):
    output.mkdir(parents=True,exist_ok=True)
    for name,character,color in [('jhenkan-d-kan','換','#facc15'),('jtranslate-d-yaku','訳','#7dd3fc')]:
        images={n:render(character,color,n,font_path) for n in SIZES}
        images[256].save(output/(name+'.png'))
        write_ico(images,output/(name+'.ico'))
        native=output/name;native.mkdir(exist_ok=True)
        for n,image in images.items():image.save(native/f'{n}.png')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--font',type=Path,default=Path(r'C:\Windows\Fonts\msgothic.ttc'))
    args=parser.parse_args()
    build(args.output,args.font)
