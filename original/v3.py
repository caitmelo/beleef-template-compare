import sys; sys.path.insert(0,'/workspace/stc2')
from comp import *
import pymupdf, numpy as np
OUT="/workspace/stone-template-compare/v3/Stone-Zander-vs-zip-v3.pdf"
D="/workspace/stone-design-zip/Fixed - matches Zander/"
ZS=D+"6x4 stock - ZANDER - 342117, 356427 Generic_Signboard 4x6 Edgewrap Portrait.pdf"; ZST=(67.3,67.3,931.9,1365.6)
DT=(45.75,45.1,910.5,1343.35)
ZB=D+"A4 Portrait - ZANDER - 347042_Brochure A4 2 page in house.pdf"; ZBT=(0,0,595.276,841.89)
DBR=D+"A4 Portrait - A4 Portrait 2 Page (stone.brochure.a4Portrait2Page).pdf"; DBT=(5.67,5.67,600.94,847.56)
RED=(0.86,0.1,0.1); BLUE=(0.1,0.35,0.95)

def bnds(f,pn,tr):
    a=render(f,pn,tr,1000); bg,o=bands(a); return [(y0,y1,x0,x1) for y0,y1,x0,x1,c in o if y1-y0>0.002]
def ink(f,pn,tr,x0,y0,x1,y1,thr=60):
    a=render(f,pn,tr,1400); H,W,_=a.shape
    bg=np.median(a[5:15,W//2-40:W//2+40].reshape(-1,3),axis=0)
    sub=a[int(y0*H):int(y1*H),int(x0*W):int(x1*W)].astype(int); m=np.abs(sub-bg).sum(2)>thr
    r=np.where(m.any(1))[0]; c=np.where(m.any(0))[0]
    return (round(x0+c.min()/W,3),round(y0+r.min()/H,3),round(x0+(c.max()+1)/W,3),round(y0+(r.max()+1)/H,3))
def sp(f,pn,tr):
    return spans(f,pn,tr)
def pc(a,b): return (a-b)/b*100
def w(b): return b[2]-b[0]
def h(b): return b[3]-b[1]

def sign_measure(f,pn,tr,kind):
    B=bnds(f,pn,tr)
    if kind=="auction":
        names=["logo","bar1","head","a1","a2","a3","bar2","names","phones","url"]
    else:
        names=["logo","bar1","head1","head2","bar2","names","phones","url"]
    assert len(B)==len(names),(f,len(B))
    M={n:b for n,b in zip(names,[(x0,y0,x1,y1) for y0,y1,x0,x1 in B])}
    S=sp(f,pn,tr)
    # columns from spans: phone spans and name spans
    ph=[s for s in S if s['t'][0].isdigit()]; nm=[s for s in S if s['font'].startswith('Poppins') and s['t'] not in('stonerealestate.com.au',) and not s['t'][0].isdigit() and s['col'].upper() in('#00B9BE','#12B9BD')]
    M['spans']=S; M['ph']=ph; M['nm']=nm
    return M

def centre(s): return (s['x0']+s['x1'])/2

def sign_pair(title,zf,zpn,zkind,df,dkind,variant,white=False,one_agent_ref=False):
    Z=sign_measure(zf,zpn,ZST,zkind); Dm=sign_measure(df,0,DT,dkind)
    items=[]; n=0
    def add(zipb,zandb,text,zip_on_zip=None):
        items.append(dict(zip=zipb,zand=zandb,text=text,ref_on_zip=zip_on_zip))
    # logo
    zl=Z['logo']; dl=Dm['logo']
    add(dl,zl,f"Logo: {abs(pc(w(dl),w(zl))):.0f}% {'wider' if w(dl)>w(zl) else 'narrower'} than Zander. It sits {abs(dl[1]-zl[1])*100:.1f}% of the board height {'higher' if dl[1]<zl[1] else 'lower'}. Zip logo is a picture (1984 x 895 px), Zander's is vector.")
    # bars
    zb=Z['bar1']; db=Dm['bar1']
    def bar(zb,db,which):
        t=[]
        if abs(pc(w(db),w(zb)))>=3: t.append(f"{abs(pc(w(db),w(zb))):.0f}% {'wider' if w(db)>w(zb) else 'narrower'}")
        if abs(pc(h(db),h(zb)))>=15: t.append(f"{'thicker' if h(db)>h(zb) else 'thinner'} ({h(db)*100:.1f}% vs {h(zb)*100:.1f}% of height)")
        dy=db[1]-zb[1]
        if abs(dy)>=0.004: t.append(f"{abs(dy)*100:.1f}% of height {'lower' if dy>0 else 'higher'}")
        return which+": "+(", ".join(t) if t else "same width and thickness as Zander, within 0.4% of height in position")+"."
    add(db,zb,bar(zb,db,"Top teal bar"))
    # heading
    if zkind=="auction":
        zh=Z['head']; dh=Dm['head']
        zs=[s for s in Z['spans'] if s['t']=='Auction'][0]; ds=[s for s in Dm['spans'] if s['t']=='Auction'][0]
        add(dh,zh,f"Heading 'Auction': font size {ds['size']:.1f} pt vs Zander {zs['size']:.1f} pt ({abs(pc(ds['size'],zs['size'])):.1f}% smaller). Word is {abs(pc(w(dh),w(zh))):.1f}% narrower and sits {abs(dh[1]-zh[1])*100:.1f}% of height higher. Font: {ds['font']} vs Zander {zs['font']}.")
        # address
        za=[Z['a1'],Z['a2'],Z['a3']]; da=[Dm['a1'],Dm['a2'],Dm['a3']]
        zu=(min(b[0] for b in za),za[0][1],max(b[2] for b in za),za[2][3]); du=(min(b[0] for b in da),da[0][1],max(b[2] for b in da),da[2][3])
        zsa=[s for s in Z['spans'] if s['t']=='36 Pendle Way'][0]; dsa=[s for s in Dm['spans'] if s['t']=='36 Pendle Way'][0]
        add(du,zu,f"Address and time lines: {dsa['size']:.1f} pt vs Zander {zsa['size']:.1f} pt ({abs(pc(dsa['size'],zsa['size'])):.0f}% smaller), so the block is {abs(pc(w(du),w(zu))):.0f}% narrower. Lines start within 0.4% of height of Zander and the font (Poppins Regular) matches.")
    else:
        h1z,h1d=Z['head1'],Dm['head1']; h2z,h2d=Z['head2'],Dm['head2']
        zs=[s for s in Z['spans'] if s['t']=='For'][0]; ds=[s for s in Dm['spans'] if s['t']=='For'][0]
        add(h1d,h1z,f"Heading 'For': font size {ds['size']:.1f} pt vs Zander {zs['size']:.1f} pt ({abs(pc(ds['size'],zs['size'])):.1f}% smaller). Word is {abs(pc(w(h1d),w(h1z))):.0f}% narrower and sits {abs(h1d[1]-h1z[1])*100:.1f}% of height higher. Font: {ds['font']} vs Zander {zs['font']}.")
        word=variant
        add(h2d,h2z,f"Heading '{word}': {abs(pc(w(h2d),w(h2z))):.0f}% narrower than Zander and sits {abs(h2d[1]-h2z[1])*100:.1f}% of height higher. Gap between the two heading lines is {abs((h2d[1]-h1d[3])-(h2z[1]-h1z[3]))*100:.1f}% of height {'bigger' if (h2d[1]-h1d[3])>(h2z[1]-h1z[3]) else 'smaller'}.")
    # bottom bar
    zb=Z['bar2']; db=Dm['bar2']; add(db,zb,bar(zb,db,"Bottom teal bar"))
    # agents
    ZS_=Z['spans']; DS_=Dm['spans']
    zph=[s for s in ZS_ if s['t'].startswith('0400')]; dph=[s for s in DS_ if s['t'][0]=='0']
    znm=[s for s in ZS_ if s['t']=='<Name>']; dnm=[s for s in DS_ if s['t'] in('Sarah Mitchell','James Carter')]
    def colbox(sl):  # union box of name+phone spans per column
        return (min(s['x0'] for s in sl),min(s['y0'] for s in sl),max(s['x1'] for s in sl),max(s['y1'] for s in sl))
    dL=colbox([dnm[0],dph[0]]); dR=colbox([dnm[1],dph[1]])
    if one_agent_ref:
        # Zander p1 has 1 agent; reference 2 agent layout from p3
        p3=sign_measure(ZS,2,ZST,"sale")  # For Lease dark p3, same 2 agent layout
        zn2=[s for s in p3['spans'] if s['t']=='<Name>']; zp2=[s for s in p3['spans'] if s['t'].startswith('0400')]
        zL=colbox([zn2[0],zp2[0]]); zR=colbox([zn2[1],zp2[1]])
        z1=colbox([znm[0],zph[0]])
        ref_names=zn2; ref_ph=zp2
        add(None,None,"")  # placeholder replaced below
        items.pop()
        items.append(dict(zip=dL,zip2=dR,zand=z1,text=f"Number of agents: Zander For Sale dark has ONE agent, centred (name {znm[0]['size']:.1f} pt, phone {zph[0]['size']:.1f} pt). Zip has TWO side by side. Zander has no 2 agent For Sale dark page, so the blue dashed boxes here show Zander's 2 agent layout from its For Lease dark page (page 3).",ref_on_zip=[zL,zR]))
    else:
        zL=colbox([znm[0],zph[0]]); zR=colbox([znm[1],zph[1]])
        ref_names=znm; ref_ph=zph
    dn=dnm[0]; dp=dph[0]; rn=ref_names[0]; rp=ref_ph[0]
    txt=(f"Agent text: names {dn['size']:.1f} pt {dn['font']} vs Zander {rn['size']:.1f} pt {rn['font']} ({pc(dn['size'],rn['size']):+.0f}%). Phones {dp['size']:.1f} pt vs {rp['size']:.1f} pt ({pc(dp['size'],rp['size']):+.0f}%). "
         f"Name baseline is {abs(dn['origy']-rn['origy'])*100:.1f}% of height {'lower' if dn['origy']>rn['origy'] else 'higher'}, phone baseline {abs(dp['origy']-rp['origy'])*100:.1f}% {'lower' if dp['origy']>rp['origy'] else 'higher'}.")
    zc=[centre(ref_ph[0]),centre(ref_ph[1])]; dc=[centre(dph[0]),centre(dph[1])]
    txt+=(f" Columns: left centre at {dc[0]*100:.1f}% of width vs Zander {zc[0]*100:.1f}% ({(dc[0]-zc[0])*100:+.1f}%), right centre at {dc[1]*100:.1f}% vs {zc[1]*100:.1f}% ({(dc[1]-zc[1])*100:+.1f}%).")
    if one_agent_ref:
        items.append(dict(zip=None,zand=None,text=txt+" (Boxes are at note 6.)",ref_on_zip=None))
    else:
        items.append(dict(zip=dL,zip2=dR,zand=zL,zand2=zR,text=txt,ref_on_zip=[zL,zR]))
    # url
    zu=Z['url']; du=Dm['url']
    zus=[s for s in ZS_ if s['t']=='stonerealestate.com.au'][0]; dus=[s for s in DS_ if s['t']=='stonerealestate.com.au'][0]
    ut=f"Website: {dus['size']:.1f} pt vs Zander {zus['size']:.1f} pt ({pc(dus['size'],zus['size']):+.0f}%), sits {abs(du[1]-zu[1])*100:.1f}% of height {'lower' if du[1]>zu[1] else 'higher'}."
    if white: ut+=" Colour: zip text renders grey (RGB 139 141 153), Zander is navy (RGB 56 67 85)."
    add(du,zu,ut)
    # colour
    bgz="#394356"; 
    ct="Colours: zip background fill #404557, Zander #394356. Teal text #12B9BD vs Zander #00B9BE."
    if white: ct="Colours: zip navy text and logo #404557, Zander #394356. Teal #12B9BD vs Zander #00B9BE."
    items.append(dict(zip=None,zand=None,text=ct,ref_on_zip=None,textonly=True))
    return items

def draw_pair(doc,title,subtitle,zsrc,zpn,ztr,dsrc,dpn,dtr,zlabel,dlabel,items):
    zr=pymupdf.Rect(*ztr); dr=pymupdf.Rect(*dtr)
    sc=720/zr.height
    pw_=zr.width*sc; ph_=zr.height*sc
    M=28; nw=450
    W=M+pw_+M+pw_+M+nw+M; H=ph_+120
    pg=doc.new_page(width=W,height=H)
    pg.insert_text((M,34),title,fontsize=17,fontname="hebo")
    pg.insert_text((M,52),subtitle,fontsize=9,fontname="helv",color=(0.25,0.25,0.25))
    zx=M; dx=M+pw_+M; y0=88
    zrect=pymupdf.Rect(zx,y0,zx+pw_,y0+ph_); drect=pymupdf.Rect(dx,y0,dx+pw_,y0+ph_)
    pg.show_pdf_page(zrect,pymupdf.open(zsrc),zpn,clip=zr)
    pg.show_pdf_page(drect,pymupdf.open(dsrc),dpn,clip=dr)
    pg.draw_rect(zrect,color=(0.5,0.5,0.5),width=0.6); pg.draw_rect(drect,color=(0.5,0.5,0.5),width=0.6)
    pg.insert_text((zx,y0-8),"ZANDER (reference)  "+zlabel,fontsize=9.5,fontname="hebo",color=BLUE)
    pg.insert_text((dx,y0-8),"ZIP (Insaram)  "+dlabel,fontsize=9.5,fontname="hebo",color=RED)
    def R(rect0,b,pad=0.004):
        return pymupdf.Rect(rect0.x0+(b[0]-pad)*pw_,rect0.y0+(b[1]-pad)*ph_,rect0.x0+(b[2]+pad)*pw_,rect0.y0+(b[3]+pad)*ph_)
    num=0; notes=[]
    dash=f"[4 3] 0"
    for it in items:
        if not it['text']: continue
        num+=1
        # blue boxes on Zander panel + on zip panel
        zb=[it[k] for k in ('zand','zand2') if it.get(k)]
        for b in zb:
            r=R(zrect,b); pg.draw_rect(r,color=BLUE,width=1.0,dashes=dash)
        if zb:
            r=R(zrect,zb[0]); pg.insert_text((r.x0-1,r.y0-3),str(num),fontsize=8.5,fontname="hebo",color=BLUE)
        refs=it.get('ref_on_zip') or ([it['zand']] if it.get('zand') else [])
        for b in refs: pg.draw_rect(R(drect,b),color=BLUE,width=1.0,dashes=dash)
        rb=[it[k] for k in ('zip','zip2') if it.get(k)]
        for b in rb: pg.draw_rect(R(drect,b),color=RED,width=1.5)
        if rb:
            r=R(drect,rb[0]); c=pymupdf.Point(min(r.x1+9,drect.x1-9),max(r.y0+4,drect.y0+9))
            pg.draw_circle(c,8,color=RED,fill=RED); pg.insert_text(pymupdf.Point(c.x-2.8*len(str(num)),c.y+3.4),str(num),fontsize=9,fontname="hebo",color=(1,1,1))
        elif it.get('textonly') is None and not rb:
            pass
        notes.append((num,it['text'],bool(rb)))
    nx=dx+pw_+M; y=y0
    pg.insert_text((nx,y0-8),"Differences (zip compared with Zander)",fontsize=9.5,fontname="hebo")
    fs=9.6
    pg.insert_text((nx,y+10),"Red box = zip item. Blue dashed box = where Zander puts it.",fontsize=7.5,fontname="heit",color=BLUE); y+=22
    for num,t,onpanel in notes:
        lines=int(pymupdf.get_text_length(t,"helv",fs)/(nw-24))+1
        hh=lines*fs*1.28+6
        pg.draw_circle(pymupdf.Point(nx+7,y+7),7,color=RED,fill=RED)
        pg.insert_text(pymupdf.Point(nx+7-2.6*len(str(num)),y+10),str(num),fontsize=8.5,fontname="hebo",color=(1,1,1))
        pg.insert_textbox(pymupdf.Rect(nx+20,y+1,nx+nw,y+hh+14),t,fontsize=fs,fontname="helv")
        y+=hh+3
    if y>y0+ph_+10: print("WARNING notes overflow",title,y,y0+ph_)
    return [(n,t) for n,t,_ in notes]

doc=pymupdf.open(); summary=[]
SZ="Zander Generic_Signboard 4x6 Edgewrap Portrait"
sb=[("Pair 1: 6x4 For Sale, dark","For Sale (6x4)  forSale6x4.pdf",ZS,0,"p1 For Sale dark, 1 agent",D+"6x4 stock - For Sale (6x4) (stone.signboard.forSale6x4).pdf","sale","Sale",False,True),
    ("Pair 2: 6x4 For Sale, white","For Sale white (6x4)  forSale6x4White.pdf",ZS,3,"p4 For Sale white, 2 agents",D+"6x4 stock - For Sale white (6x4) (stone.signboard.forSale6x4White).pdf","sale","Sale",True,False),
    ("Pair 3: 6x4 For Lease, dark","For Lease (6x4)  forLease6x4.pdf",ZS,2,"p3 For Lease dark, 2 agents",D+"6x4 stock - For Lease (6x4) (stone.signboard.forLease6x4).pdf","sale","Lease",False,False),
    ("Pair 4: 6x4 Auction, dark","Auction (6x4)  auction6x4.pdf",ZS,4,"p5 Auction dark, 2 agents",D+"6x4 stock - Auction (6x4) (stone.signboard.auction6x4).pdf","auction","",False,False),
    ("Pair 5: 6x4 Auction, white","Auction white (6x4)  auction6x4White.pdf",ZS,5,"p6 Auction white, 2 agents",D+"6x4 stock - Auction white (6x4) (stone.signboard.auction6x4White).pdf","auction","",True,False)]
for title,dlabel,zf,zpn,zlabel,df,kind,variant,white,oneagent in sb:
    items=sign_pair(title,zf,zpn,kind,df,kind,variant,white,oneagent)
    notes=draw_pair(doc,title,"Same scale, both boards cropped to the trim size (about 864 x 1298 pt).",zf,zpn,ZST,df,0,DT,zlabel,dlabel,items)
    summary.append((title,zlabel,dlabel,notes))

def bro_items(pn):
    it=[]
    it.append(dict(zip=(.048,.714,.462,.806),zand=(.048,.704,.300,.817),text="Heading font: Tinos-Bold 32 pt in zip vs NimbusRomNo9L-Med 40 pt in Zander (20% smaller). Line to line gap is 4.0% of page height vs Zander 4.8%, so the two lines sit tighter."))
    it.append(dict(zip=(.395,.753,.464,.806),zand=(.048,.751,.300,.817),text="Cut off text: the second heading line ends at 'with Effortless Fa' and the last letter is clipped at the edge of its box. Zander's heading lines fit inside the left column."))
    it.append(dict(zip=(.524,.766,.955,.821),zand=(.524,.765,.954,.834),text="Description: 7.2 pt in zip vs 9 pt in Zander (20% smaller). Line gap is 1.0% of height vs 1.3%. It is cut off with '...': the last line reads 'immediate sense of arrival, while floor-to-ceiling glass dissolves the...'. Block ends 1.3% of height higher than Zander's."))
    it.append(dict(zip=(.524,.863,.785,.881),zand=(.524,.863,.781,.894),text="Info lines: zip has one line starting 'Price:' with the value at 7.2 pt. Zander has two lines (Auction: and View:) with values at 9 pt. The zip value is cut off: it ends at 'Price Guide $2,800,000 - $2,950'."))
    it.append(dict(zip=(.766,.734,.955,.765),zand=(.694,.734,.955,.765),text="Icons: zip has 3 icons (bed 4, bath 3, car 2) starting at 76.9% of page width. Zander has 4 icons (bed, bath, car, desk) starting at 69.7%. The zip row sits one slot to the right and the 4th (desk) icon is missing. Icon shapes, line weight and the number font (Poppins Light 12 pt) match."))
    it.append(dict(zip=(.523,.851,.952,.858),zip2=(.523,.897,.952,.904),zand=(.524,.852,.952,.858),zand2=(.524,.898,.952,.904),text="Divider lines above and below the info block: zip draws them as filled bars 0.75 pt thick, Zander as 0.34 pt lines (zip is 2.2 times thicker). Position and length match."))
    it.append(dict(zip=(.751,.057,.917,.110),zip2=(.893,.858,.947,.897),zand=(.752,.057,.919,.111),zand2=(.893,.860,.946,.897),text="Logo and QR code: position and size match Zander (within 0.2%). In zip both are pictures (logo 1984 x 895 px, QR 116 x 116 px). In Zander both are vector."))
    if pn==1:
        it.append(dict(zip=(.751,.057,.917,.110),zand=None,text="Logo readability: the white logo sits on a pale part of the zip photo and is hard to read. The zip photo is also different from Zander's page 2 photo.",extra=True))
    it.append(dict(zip=None,zand=None,text="Colours: zip text #404557 vs Zander #394356. Teal heading and numbers #12B9BD vs #00B9BE. Website grey #828392 vs #878997.",textonly=True))
    if pn==0:
        ok="Matches Zander (within 0.3% of page height): photo, address, both agent blocks (Poppins SemiBold 9 pt names, Regular 9 pt phones, Regular 8 pt emails), big phone number (Poppins SemiBold 19.3 pt) and website."
    else:
        ok="Matches Zander (within 0.4% of page): big photo and the two small photos (small photo gap is 1.4% of width vs 1.0%), address, both agent blocks, big phone number and website."
    it.append(dict(zip=None,zand=None,text=ok,textonly=True,ok=True))
    return it
bro=[("Pair 6: A4 Portrait brochure, page 1 (one big photo)","A4 Portrait 2 Page, page 1  a4Portrait2Page.pdf",0),
     ("Pair 7: A4 Portrait brochure, page 2 (1 big and 2 small photos)","A4 Portrait 2 Page, page 2  a4Portrait2Page.pdf",1)]
for title,dlabel,pn in bro:
    items=bro_items(pn)
    zlabel=f"347042 Brochure A4 2 page in house, page {pn+1}"
    notes=draw_pair(doc,title,"Same scale, each page cropped to its trim size (A4, 595 x 842 pt). Zip page has 5.7 pt bleed, Zander has none.",ZB,pn,ZBT,DBR,pn,DBT,zlabel,dlabel,items)
    summary.append((title,zlabel,dlabel,notes))

# summary pages
W_,H_=595,842
pg=doc.new_page(width=W_,height=H_); y=48
def line(t,fs=9,fn="helv",gap=3,x=40,wd=515):
    global pg,y
    nl=int(pymupdf.get_text_length(t,fn,fs)/(wd-4))+1; hh=nl*fs*1.3+gap
    if y+hh>805: pg=doc.new_page(width=W_,height=H_); y=48
    pg.insert_textbox(pymupdf.Rect(x,y,x+wd,y+hh+8),t,fontsize=fs,fontname=fn); y+=hh
line("Stone Zander vs zip designs: summary (v3)",16,"hebo",8)
line("Left side is the Zander reference. Right side is Insaram's new zip design. Not a comparison with Admin. Each zip design was matched to the Zander page with the same product and variant. Differences are measured from the PDFs, in % of board or page height unless stated.",9,"heit",8)
line("Matched pairs",11,"hebo",3)
for t,z,d,n in summary: line(f"{t.split(': ',1)[0]}: zip {d.split('  ')[0]} matched to Zander {z}",9,"helv",2)
y+=4
line("Unmatched zip designs",11,"hebo",3)
line("None. All 5 signboards and both brochure pages have a Zander page with the same product and variant. One caveat: Zander For Sale dark only has a 1 agent page, the zip For Sale dark has 2 agents, so agent boxes on Pair 1 use Zander's 2 agent layout from For Lease dark.",9,"helv",6)
line("Files and page set up",11,"hebo",3)
line("Both ZANDER files in the zip folder are byte for byte the same as the Zander files downloaded from the sheet (checked by checksum). Signboard zip page is 956.7 x 1390.4 pt with 45.8 pt bleed. Zander page is 999.2 x 1432.9 pt with 67.3 pt bleed. Trim size is the same (864.8 x 1298.2 pt vs 864.6 x 1298.3 pt). Brochure zip page is 606.6 x 853.2 pt with 5.7 pt bleed. Zander brochure is A4 595.3 x 841.9 pt with no bleed.",9,"helv",6)
line("Seen on most pairs",11,"hebo",3)
for t in ["Heading font is NimbusRoman-Bold in zip. Zander uses NimbusRomNo9L-Med. Heading size is 2.7% smaller on all 5 boards.",
 "Agent names and phones use Poppins Bold in zip. Zander uses Poppins SemiBold.",
 "Colours: background #404557 vs #394356, teal #12B9BD vs #00B9BE on every pair.",
 "Logo (and on the brochure the QR code) is a picture in zip and vector in Zander.",
 "For Sale and For Lease boards: bars 21% wider, heading about 3% of height higher, agent columns closer together.",
 "Auction boards: right agent column 4.4% of width too far left, address text 6% smaller.",
 "White boards: website text is grey in zip, navy in Zander.",
 "Brochure: heading font and size differ and the heading is cut off, description 20% smaller and cut off, price cut off, desk icon missing."]: line("* "+t,9,"helv",2)
y+=6
for t,z,d,n in summary:
    line(t,11,"hebo",2); line(f"Zander: {z}.  Zip: {d}",8,"heit",2)
    for i,tx in n: line(f"{i}. {tx}",8.5,"helv",2)
    y+=4
doc.save(OUT,garbage=3,deflate=True)
print("saved",doc.page_count)
