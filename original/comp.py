import pymupdf,numpy as np,sys,json
from PIL import Image
def page(f,pn): return pymupdf.open(f)[pn]
def render(f,pn,trim,pw=1000):
    p=page(f,pn); r=pymupdf.Rect(*trim) if trim else p.rect; z=pw/r.width
    pix=p.get_pixmap(matrix=pymupdf.Matrix(z,z),clip=r)
    return np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3].copy()
def spans(f,pn,trim=None):
    p=page(f,pn); R=pymupdf.Rect(*trim) if trim else p.rect
    out=[]
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines",[]):
            for s in l["spans"]:
                if not s["text"].strip(): continue
                x0,y0,x1,y1=s["bbox"]
                out.append(dict(t=s["text"],font=s["font"],size=s["size"],sizeH=s["size"]/R.height*100,col="#%06X"%s["color"],
                    x0=(x0-R.x0)/R.width,x1=(x1-R.x0)/R.width,y0=(y0-R.y0)/R.height,y1=(y1-R.y0)/R.height,origy=(s["origin"][1]-R.y0)/R.height,bbox=s["bbox"]))
    return out
def show(f,pn,trim=None,label=""):
    p=page(f,pn); R=pymupdf.Rect(*trim) if trim else p.rect
    print(f"### {label} {f.split('/')[-1]} p{pn+1} trim={tuple(round(v,1) for v in R)} WxH={R.width:.1f}x{R.height:.1f} aspect={R.width/R.height:.4f}")
    for s in spans(f,pn,trim):
        print(f"  T {s['t'][:34]!r:38} {s['font']:22} {s['size']:6.1f}pt sizeH={s['sizeH']:.3f}% {s['col']} x {s['x0']:.3f}-{s['x1']:.3f} y {s['y0']:.3f}-{s['y1']:.3f} base={s['origy']:.3f}")
    for im in p.get_image_info():
        x0,y0,x1,y1=im["bbox"]; print(f"  IMG {im['width']}x{im['height']} x {(x0-R.x0)/R.width:.3f}-{(x1-R.x0)/R.width:.3f} y {(y0-R.y0)/R.height:.3f}-{(y1-R.y0)/R.height:.3f}")
    n=0
    for g in p.get_drawings():
        r=g["rect"]
        if r.width*r.height<4 and g.get('width',0) in (None,0): continue
        n+=1
        if n>80: break
        fl=g.get('fill'); st=g.get('color')
        h=lambda c: None if c is None else "#%02X%02X%02X"%tuple(int(round(v*255)) for v in c[:3])
        print(f"  D fill={h(fl)} stroke={h(st)} w={g.get('width')} x {(r.x0-R.x0)/R.width:.3f}-{(r.x1-R.x0)/R.width:.3f} y {(r.y0-R.y0)/R.height:.3f}-{(r.y1-R.y0)/R.height:.3f}")
def bands(a,minrow=1,thr=60,bg=None):
    H,W,_=a.shape
    if bg is None: bg=np.median(a[3:10,W//2-30:W//2+30].reshape(-1,3),axis=0)
    m=(np.abs(a.astype(int)-np.array(bg)).sum(2)>thr)
    rows=m.sum(1)>minrow; out=[]; y=0
    while y<H:
        if rows[y]:
            y0=y
            while y<H and rows[y]: y+=1
            sub=m[y0:y]; cols=np.where(sub.any(0))[0]; c=a[y0:y][sub]
            out.append((y0/H,y/H,cols[0]/W,(cols[-1]+1)/W,tuple(int(v) for v in np.median(c,axis=0))))
        y+=1
    return bg,out
def pb(a,label,**k):
    bg,o=bands(a,**k); print("## bands",label,"bg",[int(v) for v in bg])
    for y0,y1,x0,x1,c in o:
        if y1-y0>0.002: print(f"   y {y0:.3f}-{y1:.3f} h={y1-y0:.3f}  x {x0:.3f}-{x1:.3f} w={x1-x0:.3f} cx={(x0+x1)/2:.3f} col={c}")
def side(pairs,out,h=900):
    ims=[Image.fromarray(a) for a in pairs]; ims=[i.resize((int(i.width*h/i.height),h)) for i in ims]
    c=Image.new('RGB',(sum(i.width+12 for i in ims),h),(255,0,0)); x=0
    for i in ims: c.paste(i,(x,0)); x+=i.width+12
    c.save(out)
