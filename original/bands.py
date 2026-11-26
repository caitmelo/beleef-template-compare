import pymupdf,numpy as np,sys
from PIL import Image
def render(f,trim,pw=1000,pn=0):
    d=pymupdf.open(f);p=d[pn]
    r=pymupdf.Rect(*trim);z=pw/r.width
    pix=p.get_pixmap(matrix=pymupdf.Matrix(z,z),clip=r)
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3].copy()
    return a
def bands(a,name,minrow=1):
    H,W,_=a.shape
    bg=np.median(a[5:15,W//2-50:W//2+50].reshape(-1,3),axis=0)
    m=(np.abs(a.astype(int)-bg).sum(2)>60)
    # ignore watermarks? keep
    rows=m.sum(1)>minrow
    out=[];y=0
    while y<H:
        if rows[y]:
            y0=y
            while y<H and rows[y]: y+=1
            sub=m[y0:y];cols=np.where(sub.any(0))[0]
            c=a[y0:y][sub]
            # dominant colour
            cc=tuple(int(v) for v in np.median(c,axis=0))
            out.append((y0/H,y/H,cols[0]/W,(cols[-1]+1)/W,(y-y0)/H,cc))
        y+=1
    print("##",name,"bg",bg.astype(int),"size",W,H)
    for o in out:
        if o[4]>0.002: print(f" y {o[0]:.3f}-{o[1]:.3f} h={o[4]:.3f} x {o[2]:.3f}-{o[3]:.3f} w={o[3]-o[2]:.3f} cx={(o[2]+o[3])/2:.3f} col={o[5]}")
    return out
if __name__=="__main__":
    T=(157.3,128.98,3556.1,5228.5);D=(45.75,45.1,910.5,1343.35)
    t=render("stone-group-templates/central-coast/6x4 portrait.pdf",T);bands(t,"TEMPLATE CC 6x4 portrait")
    Image.fromarray(t).save("stc/t_cc6x4.png")
    import glob
    for f in sorted(glob.glob("stone-design-zip/Fixed - matches Zander/6x4 stock - [AF]*.pdf"))+["stc/caitlin.pdf"]:
        a=render(f,D);bands(a,f.split('/')[-1]);Image.fromarray(a).save("stc/d_"+f.split('/')[-1][:30].replace(' ','_')+".png")
