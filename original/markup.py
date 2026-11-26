import pymupdf, os
Z="stone-design-zip/Fixed - matches Zander/"
OUT="stone-template-compare/v1/"
RED=(0.86,0.1,0.1); BLUE=(0.1,0.35,0.95)
D=(45.75,45.1,910.5,1343.35)
def P(fx0,fy0,fx1,fy1):
    w=D[2]-D[0];h=D[3]-D[1]
    return pymupdf.Rect(D[0]+fx0*w,D[1]+fy0*h,D[0]+fx1*w,D[1]+fy1*h)

def build(src, out, title, matched, pages_issues, header_note=""):
    """pages_issues: list per source page of list of (n, red_rects, blue_rects, note)"""
    s=pymupdf.open(src); o=pymupdf.open()
    allnotes=[]
    for pn,issues in enumerate(pages_issues):
        sp=s[pn]; W,H=sp.rect.width,sp.rect.height
        pw=W*1.75; page=o.new_page(width=pw,height=H)
        page.show_pdf_page(pymupdf.Rect(0,0,W,H),s,pn)
        fs=W/45  # note font size
        for n,reds,blues,note in issues:
            for r in blues:
                page.draw_rect(r,color=BLUE,width=fs*0.18,dashes=f"[{fs*0.6} {fs*0.4}] 0")
            for r in reds:
                page.draw_rect(r,color=RED,width=fs*0.22)
            if reds:
                r=reds[0]; c=pymupdf.Point(min(r.x1+fs*1.1,W-fs*1.1), r.y0+fs*0.2)
                c=pymupdf.Point(c.x, max(c.y,fs*1.1))
                page.draw_circle(c,fs*0.9,color=RED,fill=RED)
                page.insert_text(pymupdf.Point(c.x-fs*0.32*len(str(n)),c.y+fs*0.4),str(n),fontsize=fs*1.1,color=(1,1,1),fontname="hebo")
        # notes panel
        x0=W+fs; y=fs*2
        page.draw_rect(pymupdf.Rect(W,0,pw,H),color=None,fill=(0.97,0.97,0.97))
        page.insert_text(pymupdf.Point(x0,y),title,fontsize=fs*1.05,fontname="hebo",color=(0,0,0)); y+=fs*1.6
        page.insert_textbox(pymupdf.Rect(x0,y,pw-fs,y+fs*6),f"Page {pn+1}. Compared with: {matched}",fontsize=fs*0.75,fontname="helv",color=(0.2,0.2,0.2)); y+=fs*3.2
        if header_note:
            rc=page.insert_textbox(pymupdf.Rect(x0,y,pw-fs,y+fs*8),header_note,fontsize=fs*0.75,fontname="helv",color=(0.2,0.2,0.2)); y+=fs*8+rc
        page.insert_textbox(pymupdf.Rect(x0,y,pw-fs,y+fs*3),"Red box = design element with the issue. Blue dashed box = where the Admin template puts it.",fontsize=fs*0.7,fontname="heit",color=BLUE); y+=fs*2.6
        for n,reds,blues,note in issues:
            page.draw_circle(pymupdf.Point(x0+fs*0.6,y+fs*0.55),fs*0.6,color=RED,fill=RED)
            page.insert_text(pymupdf.Point(x0+fs*0.6-fs*0.22*len(str(n)),y+fs*0.85),str(n),fontsize=fs*0.75,color=(1,1,1),fontname="hebo")
            box=pymupdf.Rect(x0+fs*1.6,y,pw-fs,H)
            # estimate lines
            lines=max(1,int(pymupdf.get_text_length(note,"helv",fs*0.8)/(box.width*0.95))+1)
            page.insert_textbox(pymupdf.Rect(box.x0,y,box.x1,y+lines*fs*1.1+fs),note,fontsize=fs*0.8,fontname="helv",color=(0,0,0))
            y+=lines*fs*1.05+fs*0.9
            allnotes.append((pn+1,n,note))
    o.save(out,garbage=3,deflate=True)
    return allnotes

# template element positions (trim fractions) from CC 6x4 portrait
TL=P(.324,.086,.677,.192); TBT=P(.447,.278,.552,.287); TL1=P(.319,.337,.682,.452); TL2=P(.291,.489,.713,.609)
TBB=P(.446,.674,.553,.682); TNAMES=[P(.075,.764,.469,.792),P(.583,.764,.864,.792)]; TPH=[P(.105,.793,.414,.830),P(.553,.793,.903,.830)]
TURL=P(.311,.929,.689,.944)
M_SB="Admin Groups > Stone Central Coast > 6x4 portrait.pdf (For Sale, dark, 2 agents, 1200 x 1800 mm trim)"

def sale_issues(white=False, lease=False):
    word="Lease" if lease else "Sale"
    iss=[
     (1,[P(.331,.096,.671,.198)],[TL],"Logo is 4% smaller and sits 18 mm lower than the template."),
     (2,[P(.444,.280,.557,.290)],[TBT],"Top teal bar is 8% wider and about 20% thicker than the template."),
     (3,[P(.341,.316,.664,.418),P(.316 if not lease else .239,.471,.691 if not lease else .765,.577)],[TL1,TL2],
        f"Heading 'For {word}' is about 11% smaller than the template. 'For' starts 38 mm higher and the gap between the two lines is 29 mm bigger. Font shape matches."),
     (4,[P(.444,.668,.557,.678)],[TBB],"Bottom teal bar sits 11 mm higher and is thicker than the template."),
     (5,[P(.154,.765,.451,.789),P(.551,.765,.834,.789)],TNAMES,"Agent names and phones use Poppins Bold. Template uses Poppins SemiBold. Names are 7% bigger, phones 3% smaller than the template."),
     (6,[P(.148,.804,.457,.840),P(.532,.804,.852,.840)],TPH,"Agent columns sit too close to the middle: left column 52 mm and right column 43 mm further in. Phone line sits 18 mm lower, so the name to phone gap is bigger."),
     (7,[P(.294,.924,.706,.948)],[TURL],"Website text is 8% bigger than the template."),
    ]
    if white:
        iss.append((8,[],[],"No white version exists in Admin Groups. Layout was checked against the dark template, colours could not be checked."))
    else:
        iss.append((8,[],[],"Colours: background is #404557, template reads about #3B4455 (template is a picture, so this is approximate). Teal is #12B9BD, template text teal is #00B9BE. Small, check with print proof."))
    return iss

def auction_issues(white=False, caitlin=False):
    iss=[
     (1,[P(.341,.123,.660,.218)],[TL],"Logo is 10% smaller and sits 67 mm lower than the template. It is also a different size and spot from the dev For Sale and For Lease boards."),
     (2,[P(.455,.291,.547,.299),P(.455,.658,.547,.666)],[TBT,TBB],"Teal bars are 12% narrower than the template. Top bar sits 23 mm lower, bottom bar 29 mm higher. Also differ from the dev For Sale boards."),
     (3,[P(.136,.326,.867,.430)],[],"Heading uses the same font size as the dev For Sale boards, which is about 11% smaller than the Admin For Sale heading. There is no Auction version in Admin to check the word itself."),
     (4,[P(.258,.507,.742,.610)],[],"Address and auction time lines do not exist in the Admin template, so they could not be checked against Admin. Position matches the Zander reference."),
     (5,[P(.164,.758,.408,.777),P(.592,.758,.824,.777)],TNAMES,"Agent names and phones use Poppins Bold, template uses SemiBold. Names are 12% smaller and phones 3% bigger than the template. Sizes also differ from the dev For Sale boards."),
     (6,[P(.122,.795,.450,.821),P(.538,.795,.878,.821)],TPH,"Agent columns sit too close to the middle: left 31 mm, right 24 mm further in. Names sit 25 mm higher and phones 18 mm higher than the template."),
     (7,[P(.327,.908,.674,.922)],[TURL],"Website text is 9% smaller than the template, and smaller than on the dev For Sale boards."),
    ]
    if white: iss.append((8,[],[],"No white version exists in Admin Groups. Layout was checked against the dark template, colours could not be checked."))
    else: iss.append((8,[],[],"Colours: background is #404557, template reads about #3B4455 (approximate, template is a picture). Teal is #12B9BD, template text teal is #00B9BE."))
    return iss

summ=[]
jobs=[
 ("6x4 stock - For Sale (6x4) (stone.signboard.forSale6x4).pdf","markup-v1 For Sale 6x4.pdf","For Sale 6x4 (dark)",sale_issues()),
 ("6x4 stock - For Sale white (6x4) (stone.signboard.forSale6x4White).pdf","markup-v1 For Sale white 6x4.pdf","For Sale 6x4 (white)",sale_issues(white=True)),
 ("6x4 stock - For Lease (6x4) (stone.signboard.forLease6x4).pdf","markup-v1 For Lease 6x4.pdf","For Lease 6x4 (dark)",sale_issues(lease=True)),
 ("6x4 stock - Auction (6x4) (stone.signboard.auction6x4).pdf","markup-v1 Auction 6x4.pdf","Auction 6x4 (dark)",auction_issues()),
 ("6x4 stock - Auction white (6x4) (stone.signboard.auction6x4White).pdf","markup-v1 Auction white 6x4.pdf","Auction 6x4 (white)",auction_issues(white=True)),
]
for src,out,title,iss in jobs:
    hn="For Lease: no For Lease version in Admin, so the For Sale template layout was used." if "Lease" in title else ""
    summ.append((title,M_SB,build(Z+src,OUT+out,title,M_SB,[iss],hn)))
# Caitlin's PDF
summ.append(("Caitlin design: Auction 6x4, 36 Pendle Way",M_SB,build("stc/caitlin.pdf",OUT+"markup-v1 Caitlin Auction 36 Pendle Way.pdf","Caitlin design: Auction 36 Pendle Way",M_SB,[auction_issues()],
  "This file is byte for byte the same as the dev file 'Auction (6x4)', so the same issues apply.")))

# Brochure
R=pymupdf.Rect
M_BR="No fair Admin match. Brand items checked against Admin A4 brochures: Central Coast A4 Doublesided.pdf and Parramatta Professional Brochure (1).pdf (both landscape). Zander ref used for layout."
def br(pn):
    iss=[
     (1,[R(34,606.8,281,684.5)],[],"Heading font is Tinos Bold 32 pt. Admin brochures use Nimbus Roman No9 L Medium (40 pt Parramatta, 45 pt Central Coast, 40 pt Zander)."),
     (2,[R(250,641,292,684.5)],[],"Heading line 2 overflows and is cut off: shows 'with Effortless Fa'."),
     (3,[R(316,650,577,698)],[],"Description is 7.2 pt and cut off with '...'. Admin brochures and Zander use 9 pt Poppins Regular."),
     (4,[R(358,733,476,747)],[],"Price is cut off: shows 'Price Guide $2,800,000 - $2,950'."),
    ]
    if pn==1: iss.append((5,[R(453,54.1,551.2,98.3)],[],"White logo sits on a light part of the photo and is hard to see."))
    iss.append((6 if pn==1 else 5,[],[],"Layout: Admin Groups has no A4 portrait brochure like this. Central Coast and Parramatta A4 brochures are landscape with a navy footer, and the Parramatta AB brochure is a different portrait layout. So page layout was not marked against Admin."))
    iss.append((7 if pn==1 else 6,[],[],"Icons (bed, bath, car) match the Admin brochure icon shapes. Number font Poppins Light 12 pt matches. No issue."))
    return iss
summ.append(("A4 Portrait 2 Page brochure",M_BR,build(Z+"A4 Portrait - A4 Portrait 2 Page (stone.brochure.a4Portrait2Page).pdf",OUT+"markup-v1 A4 Portrait 2 Page brochure.pdf","A4 Portrait 2 Page brochure",M_BR,[br(0),br(1)])))

# combined with summary page
comb=pymupdf.open()
for src,out,title,iss in jobs: comb.insert_pdf(pymupdf.open(OUT+out))
comb.insert_pdf(pymupdf.open(OUT+"markup-v1 Caitlin Auction 36 Pendle Way.pdf"))
comb.insert_pdf(pymupdf.open(OUT+"markup-v1 A4 Portrait 2 Page brochure.pdf"))
lines=[]
for title,m,notes in summ:
    lines.append(("h",title)); lines.append(("m","Matched to: "+m))
    seen=set()
    for pg,n,note in notes:
        key=(n,note)
        if key in seen: continue
        seen.add(key); lines.append(("n",f"{n}. "+note))
lines.append(("h","Not matched"))
lines.append(("n","A4 Portrait brochure: no fair Admin layout match (see above)."))
lines.append(("n","Admin templates with no dev design yet: Parramatta 6x4 Photo Signboard, 8x4 signboards, 6 x 2, One photo 6 x 4, AB brochure, Professional Brochure, DL mailcards."))
lines.append(("n","Zander reference files were used as extra reference only and not marked up."))
pg=comb.new_page(width=595,height=842); y=50
pg.insert_text((40,y),"Summary of issues (v1)",fontsize=16,fontname="hebo"); y+=24
for kind,t in lines:
    fs={"h":11,"m":8,"n":8.5}[kind]; fn={"h":"hebo","m":"heit","n":"helv"}[kind]
    nl=int(pymupdf.get_text_length(t,fn,fs)/505)+1; hgt=nl*fs*1.3+4
    if y+hgt>810: pg=comb.new_page(width=595,height=842); y=50
    if kind=="h": y+=6
    pg.insert_textbox(R(40,y,555,y+hgt+6),t,fontsize=fs,fontname=fn); y+=hgt
comb.save(OUT+"Stone-template-markup-v1.pdf",garbage=3,deflate=True)
print("ok",comb.page_count)
