import pymupdf,sys
def dump(f):
    d=pymupdf.open(f)
    for pn,p in enumerate(d):
        print("=====",f,pn+1,"rect",p.rect,"crop",p.cropbox,"trim",p.trimbox,"bleed",p.bleedbox,"media",p.mediabox)
        W,H=p.rect.width,p.rect.height
        for b in p.get_text("dict")["blocks"]:
            if b["type"]==0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        if not s["text"].strip(): continue
                        x0,y0,x1,y1=s["bbox"]
                        print(f"T {s['text'][:40]!r:44} font={s['font']} size={s['size']:.1f} ({s['size']/H*1000:.2f}‰H) col=#{s['color']:06x} x0={x0/W:.3f} x1={x1/W:.3f} y0={y0/H:.3f} y1={y1/H:.3f} cx={(x0+x1)/2/W:.3f}")
        for im in p.get_image_info(xrefs=True):
            x0,y0,x1,y1=im["bbox"];print(f"IMG {im['width']}x{im['height']} x0={x0/W:.3f} x1={x1/W:.3f} y0={y0/H:.3f} y1={y1/H:.3f}")
        dr=p.get_drawings()
        print("drawings",len(dr))
        for g in dr[:60]:
            r=g["rect"]
            if r.width*r.height<1: continue
            print(f"D fill={g.get('fill')} stroke={g.get('color')} x0={r.x0/W:.3f} x1={r.x1/W:.3f} y0={r.y0/H:.3f} y1={r.y1/H:.3f} w={r.width/W:.3f} h={r.height/H:.4f}")
for f in sys.argv[1:]: dump(f)
