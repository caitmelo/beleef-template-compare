import pymupdf
OUT="stone-template-compare/v2/"
RED=(0.86,0.1,0.1); BLUE=(0.1,0.35,0.95)
D="stone-sheet-designs/"
def R(trim,b): x0,y0,x1,y1=trim; w=x1-x0; h=y1-y0; return pymupdf.Rect(x0+b[0]*w,y0+b[1]*h,x0+b[2]*w,y0+b[3]*h)
def build(out, pages):
    """pages: list of dict(src,pn,trim,title,matched,note,issues=[(n,[red fr],[blue fr],text)])"""
    o=pymupdf.open(); allnotes=[]
    for P in pages:
        s=pymupdf.open(P['src']); sp=s[P['pn']]; W,H=sp.rect.width,sp.rect.height
        trim=P['trim'] or (0,0,W,H)
        landscape=W>H
        if landscape: pw,ph=W,H*2.0
        else: pw,ph=W*1.8,H
        page=o.new_page(width=pw,height=ph)
        page.show_pdf_page(pymupdf.Rect(0,0,W,H),s,P['pn'])
        fs=min(W,H)/(28 if landscape else (42 if W/H>0.5 else 24))
        lw=fs*0.15
        for n,reds,blues,txt in P['issues']:
            for b in blues: page.draw_rect(R(trim,b),color=BLUE,width=lw,dashes=f"[{fs*0.5} {fs*0.35}] 0")
            for b in reds: page.draw_rect(R(trim,b),color=RED,width=lw*1.3)
            if reds or blues:
                r=R(trim,(reds or blues)[0])
                c=pymupdf.Point(min(r.x1+fs*0.9,W-fs*0.9),max(r.y0+fs*0.3,fs*0.9))
                page.draw_circle(c,fs*0.75,color=RED,fill=RED)
                page.insert_text(pymupdf.Point(c.x-fs*0.28*len(str(n)),c.y+fs*0.35),str(n),fontsize=fs*0.95,color=(1,1,1),fontname="hebo")
        if landscape: box=pymupdf.Rect(fs,H+fs,pw-fs,ph-fs/2); page.draw_rect(pymupdf.Rect(0,H,pw,ph),color=None,fill=(0.97,0.97,0.97))
        else: box=pymupdf.Rect(W+fs,fs,pw-fs,ph-fs); page.draw_rect(pymupdf.Rect(W,0,pw,ph),color=None,fill=(0.97,0.97,0.97))
        nf=fs*0.62; x0=box.x0; y=box.y0+nf*1.4
        def para(t,font="helv",col=(0,0,0),size=nf,indent=0):
            nonlocal y
            width=box.x1-x0-indent
            lines=max(1,int(pymupdf.get_text_length(t,font,size)/(width*0.93))+1)
            hh=lines*size*1.25+size*0.5
            page.insert_textbox(pymupdf.Rect(x0+indent,y,box.x1,y+hh+size),t,fontsize=size,fontname=font,color=col)
            y+=hh
        y-=nf*1.2; para(P['title'],"hebo",(0,0,0),nf*1.25)
        para("Compared with Admin: "+P['matched'],"heit",(0.2,0.2,0.2),nf*0.9)
        if P.get('note'): para(P['note'],"heit",(0.2,0.2,0.2),nf*0.9)
        para("Red box = design element with the issue. Blue dashed box = where the Admin template puts it.","heit",BLUE,nf*0.85)
        for n,reds,blues,txt in P['issues']:
            page.draw_circle(pymupdf.Point(x0+nf*0.55,y+nf*0.55),nf*0.55,color=RED,fill=RED)
            page.insert_text(pymupdf.Point(x0+nf*0.55-nf*0.2*len(str(n)),y+nf*0.85),str(n),fontsize=nf*0.75,color=(1,1,1),fontname="hebo")
            para(txt,indent=nf*1.5)
            allnotes.append((P['title'],n,txt))
        if y>box.y1: print("WARNING overflow",P['title'],y,box.y1)
    o.save(OUT+out,garbage=3,deflate=True); return allnotes

S64=D+"stock-6x4/342117, 356427 Generic_Signboard 4x6 Edgewrap Portrait.pdf"; T64=(67.3,67.3,931.9,1365.6)
M64="Central Coast > 6x4 portrait.pdf (For Sale, dark, 2 agents)"
c64=[ (1,[(.336,.109,.665,.209)],[(.324,.086,.677,.192)],"Logo is 7% smaller and sits 41 mm lower than Admin."),
      (2,[(.454,.285,.547,.293)],[(.447,.278,.552,.287)],"Top teal bar is 11% narrower and 13 mm lower."),
      (3,[(.334,.351,.668,.454),(.304,.500,.701,.607)],[(.319,.337,.682,.452),(.291,.489,.713,.609)],"Heading is about 10% smaller. 'For' starts 25 mm lower and the gap between the two lines is 16 mm bigger. Font shape matches."),
      (4,[(.454,.662,.547,.671)],[(.446,.674,.553,.682)],"Bottom teal bar is 11% narrower and 22 mm higher."),]
url64=lambda n:(n,[(.321,.915,.679,.929)],[(.311,.929,.689,.944)],"Website text is 5% smaller and sits 25 mm higher.")
pages64=[
 dict(src=S64,pn=0,trim=T64,title="6x4 stock: For Sale, dark (page 1)",matched=M64,issues=c64+[
   (5,[(.282,.742,.718,.859)],[(.075,.764,.903,.847)],"Agent block: Zander has 1 agent in the middle, Admin has 2 agents side by side. Admin has no 1 agent version, so this size was not compared. Font Poppins SemiBold matches."),
   url64(6)]),
 dict(src=S64,pn=2,trim=T64,title="6x4 stock: For Lease, dark (page 3)",matched=M64,note="Admin has no For Lease 6x4, so the For Sale layout was used. The word 'Lease' was not compared.",issues=[c64[0],c64[1],
   (3,[(.334,.351,.668,.454)],[(.319,.337,.682,.452)],"'For' is about 10% smaller and starts 25 mm lower. Font shape matches."),c64[3],
   (5,[(.214,.759,.360,.798),(.679,.759,.825,.798)],[(.075,.764,.469,.805),(.583,.764,.864,.805)],"Agent names are 8% smaller and phones 7% bigger than Admin. Names sit 14 mm higher."),
   (6,[(.104,.788,.470,.847),(.570,.788,.934,.847)],[(.105,.793,.414,.847),(.553,.793,.903,.847)],"Both agent columns sit about 30 mm further right than Admin."),
   url64(7)]),
]
S62=D+"stock-6x2/342119_Signboard 6x2 Edgewrap Portrait.pdf"; T62=(60.2,60.2,485.4,1357.1)
M62="Central Coast > 6 x 2.pdf (For Lease, dark, phone only)"
def c62(label_box,phone_box,what):
    return [(1,[(.235,.132,.767,.210)],[(.183,.109,.819,.205)],"Logo is 16% narrower and sits 41 mm lower than Admin."),
     (2,[(.406,.308,.596,.316)],[(.414,.330,.587,.337)],"Top teal bar is 10% wider and sits 40 mm higher."),
     (3,[(.265,.409,.739,.483),(.110,.518,.892,.592)],[(.250,.410,.754,.488),(.097,.514,.905,.591)],"Heading 'For Lease' is about 4% smaller. Position and font match."),
     (4,[(.406,.684,.596,.692)],[(.413,.644,.589,.651)],"Bottom teal bar sits 72 mm lower and is 10% wider."),
     (5,[label_box],[],f"Extra teal {what} label above the number. Admin has the number only."),
     (6,[phone_box],[(.183,.786,.817,.850)],"Phone number text is 5% bigger and sits 31 mm lower."),
     (7,[(.135,.910,.865,.943)],[(.196,.938,.804,.951)],"Website text is 19% bigger and sits 38 mm higher."),
     (8,[],[],"Board shape: Zander trim is 1.5% taller for the same width than the Admin 600 x 1800 mm board. Check the print size.")]
pages62=[dict(src=S62,pn=2,trim=T62,title="6x2 stock: For Lease, dark, agent label (page 3)",matched=M62,issues=c62((.103,.776,.897,.811),(.100,.803,.900,.872),"agent name")),
         dict(src=S62,pn=6,trim=T62,title="6x2 stock: For Lease, dark, office label (page 7)",matched=M62,issues=c62((.153,.776,.847,.811),(.165,.803,.835,.872),"office name"))]
SPB=D+"photoboard-landscape-6x4/Signboard 4x6 Bannerwrap Landscape.pdf"; TPB=(82.2,82.2,1380.5,946.8)
pagesPB=[dict(src=SPB,pn=4,trim=TPB,title="6x4 photo board landscape: bottom band, 2 agents (page 5)",
 matched="Central Coast > One photo 6 x 4.pdf (1800 x 1200 mm, bottom band, 2 agents)",
 note="Parramatta '6x4 Photo Signboard' was not used: its page is 4:3, not the 6x4 shape.",issues=[
 (1,[(.034,.051,.966,.775)],[(.055,.078,.942,.765)],"Photo is bigger than Admin: 38 mm further out on the left, 41 mm on the right, 32 mm higher at the top and 12 mm lower at the bottom."),
 (2,[(.063,.581,.197,.757)],[(.080,.598,.361,.741)],"Heading is 10% bigger, starts 31 mm further left and sits 19 mm lower. Teal is #00B9BE, Admin #00B2BE."),
 (3,[(.035,.789,.164,.849)],[(.058,.775,.153,.832)],"Address is 9% bigger, starts 41 mm further left and sits 17 mm lower."),
 (4,[(.037,.830,.267,.880)],[(.059,.843,.300,.880)],"Icons row starts 40 mm further left. Icon shapes look the same. Admin icons and numbers are a picture, so their font could not be checked."),
 (5,[(.035,.893,.322,.950)],[(.058,.880,.306,.933)],"Auction and View lines are 7% bigger. The time text starts right after the label, Admin lines it up to the right end of the line."),
 (6,[(.423,.787,.641,.960)],[(.428,.784,.536,.942)],"Agent names and phones are 16% bigger than Admin."),
 (7,[(.815,.846,.966,.947)],[(.805,.837,.946,.932)],"Logo is 7% bigger and sits 36 mm further right."),
 (8,[(.913,.696,.965,.774)],[(.898,.697,.944,.766)],"QR code is 13% bigger and sits 38 mm further right."),])]
SA4=D+"a4-landscape-2page/347152_Brochure-A4-2-Page-Landscape.pdf"
pagesA4=[dict(src=SA4,pn=2,trim=None,title="A4 Landscape 2 page: cover, bottom band (page 3)",matched="Parramatta > Professional Brochure (1).pdf page 1",issues=[
 (1,[(.663,.900,.862,.940)],[(.838,.843,.962,.877)],"Icons are in the wrong place. Admin puts them top right above the line. Zander puts them inside the lined box."),
 (2,[],[(.665,.905,.715,.932)],"Sale line ('For Sale:' or Auction) is missing. Admin has it inside the lined box."),
 (3,[(.067,.845,.190,.898)],[(.039,.850,.192,.897)],"Address starts 8 mm further right. Admin lines it up with the photo edge."),
 (4,[(.810,.900,.862,.940)],[],"Extra 4th icon (desk). Admin icon set is bed, bath and car only."),
 (5,[],[],"Heading, description, phone, website, QR, logo, photo and navy band all match Admin.")]),
 dict(src=SA4,pn=3,trim=None,title="A4 Landscape 2 page: back, 3 photos, floor plan, headshots (page 4)",matched="Parramatta > Professional Brochure (1).pdf page 2",issues=[
 (1,[],[(.869,.079,.960,.130)],"Logo is missing. Admin has it top right."),
 (2,[(.262,.715,.500,.760)],[(.257,.079,.414,.116)],"Address heading is missing at the top. Zander puts the address under the floor plan."),
 (3,[(.040,.847,.333,.951)],[(.041,.846,.165,.905)],"First footer column is a paragraph. Admin uses a bullet list here."),
 (4,[(.717,.919,.939,.941)],[],"Typo in email: 'tonerealestate' is missing the s."),
 (5,[],[],"Photo column, bullet column and agent style (headshot, teal name, phone, email) match Admin. Zander shows 2 agents, Admin 1.")])]
SJL=D+"dl-just-listed/356814_Mailcard DL Landscape Just Listed.pdf"; TDL=(5.7,5.7,600.9,286.3)
pagesJL=[dict(src=SJL,pn=0,trim=TDL,title="DL Just Listed: front (page 1)",matched="Central Coast > Just Listed DL One Agent.pdf page 1",issues=[
 (1,[(.057,.116,.146,.170)],[(.061,.151,.146,.194)],"'JUST LISTED' uses Poppins SemiBold 9 pt. Admin uses Myriad Pro Regular 10 pt. Sits 3 mm higher."),
 (2,[(.057,.121,.136,.342)],[(.060,.174,.174,.395)],"Street number is the same size (45 pt) but sits 5 mm higher."),
 (3,[(.057,.312,.185,.424)],[(.060,.359,.313,.502)],"Address is 11 pt. Admin is 14 pt, so it is 21% smaller."),
 (4,[(.057,.456,.300,.525)],[(.064,.496,.280,.602)],"Icon numbers are Poppins Light 12 pt. Admin uses Poppins Regular 13 pt. Row sits 7 mm higher and has an extra 4th icon (desk)."),
 (5,[(.333,.061,.381,.162)],[(.298,.518,.331,.589)],"QR code moved to the top of the panel and is 45% bigger. Admin puts it at the end of the icons row."),
 (6,[(.057,.571,.357,.810)],[(.061,.623,.361,.847)],"Description paragraph is missing. Zander shows Auction and View lines and 2 agents instead."),
 (7,[(.057,.848,.200,.890)],[(.061,.854,.184,.890)],"Website text is Poppins Bold 6.9 pt. Admin is Poppins SemiBold 6 pt."),
 (8,[],[(.836,.081,.962,.202)],"Admin shows a blank white box top right (its logo image does not show), so the logo could not be compared.")]),
 dict(src=SJL,pn=2,trim=TDL,title="DL Just Listed: back, heading and paragraph, 1 photo (page 3)",matched="Central Coast > Just Listed DL One Agent.pdf page 2",issues=[
 (1,[(.057,.086,.333,.306)],[(.062,.198,.343,.537)],"Heading is serif Nimbus Roman 26 pt in white and teal. Admin uses Poppins Medium 14 pt white message text."),
 (2,[(.057,.436,.357,.796)],[],"Long paragraph is extra. Admin has no paragraph."),
 (3,[],[(.061,.584,.290,.778)],"Agent block is missing. Admin has a headshot, teal name and phone at 11 pt."),
 (4,[(.057,.848,.200,.890)],[(.059,.850,.182,.886)],"Website text is Poppins Bold 6.9 pt. Admin is Poppins SemiBold 6 pt.")])]
SJS=D+"dl-just-sold/356834_Mailcard DL Landscape Just Sold - with sold price.pdf"
pagesJS=[dict(src=SJS,pn=0,trim=TDL,title="DL Just Sold: front, SOLD circle (page 1)",matched="Parramatta > Double sided DL Mailcard_Just Sold (1).pdf page 1",issues=[
 (1,[(.057,.060,.136,.281)],[(.058,.166,.234,.259)],"Headline is the street number at 45 pt. Admin headline is the sold price at 26 pt."),
 (2,[(.057,.391,.169,.457)],[(.058,.390,.166,.449)],"Property type line is missing (Admin 'Apartment', 12 pt teal). Zander puts the price here at 11 pt."),
 (3,[(.238,.496,.300,.566)],[],"Extra 4th icon (desk). Admin icon set is bed, bath and car only."),
 (4,[],[],"Panel, SOLD circle, logo, address, icon numbers, lines, QR, agent row and website match Admin.")]),
 dict(src=SJS,pn=3,trim=TDL,title="DL Just Sold: back, heading, paragraph, photo (page 4)",matched="Parramatta > Double sided DL Mailcard_Just Sold (1).pdf page 2",issues=[
 (1,[(.028,.062,.381,.937)],[(.028,.062,.448,.938)],"Text panel is 14 mm narrower than Admin."),
 (2,[(.057,.086,.333,.306)],[(.058,.120,.129,.277)],"Heading is 26 pt. Admin 'Just Sold' heading is 22 pt, so it is 18% bigger."),
 (3,[(.057,.298,.185,.410)],[(.059,.314,.250,.354)],"Address is 2 lines in Poppins Medium 11 pt. Admin is 1 line in Poppins Regular 8 pt."),
 (4,[(.057,.432,.348,.716)],[(.059,.384,.399,.639)],"Body text is Poppins Regular 9 pt with an extra teal sub heading. Admin body is Poppins SemiBold 8 pt with no sub heading."),
 (5,[(.057,.733,.357,.826)],[(.058,.702,.339,.824)],"Agent block has no email or social handle. Admin shows both."),
 (6,[],[(.399,.837,.448,.939)],"QR code is missing. Admin has it bottom right of the panel."),
 (7,[(.825,.060,.963,.165)],[],"Logo is white. Admin logo is navy.")])]
groups=[("v2 markup 6x4 stock boards.pdf",pages64),("v2 markup 6x2 stock boards.pdf",pages62),("v2 markup 6x4 photo board landscape.pdf",pagesPB),
        ("v2 markup A4 Landscape 2 page brochure.pdf",pagesA4),("v2 markup DL Just Listed.pdf",pagesJL),("v2 markup DL Just Sold.pdf",pagesJS)]
summary=[]
for fn,pg in groups:
    notes=build(fn,pg); summary.append((fn,pg,notes))
# combined
comb=pymupdf.open()
for fn,_,_ in summary: comb.insert_pdf(pymupdf.open(OUT+fn))
notcomp=["Portrait photoboard 3x4 (2 and 3 agents) and the 6x4 and 8x4 portrait versions: no Admin Groups template.",
"6x4 landscape photo boards, side panel versions (pages 1 to 4): no Admin template. Bottom band with 3 agents (page 6): Admin only has a 2 agent version.",
"6x4 landscape 3 photo collage: ours only, no Zander file.",
"6x2 For Sale dark and teal, and For Lease teal (pages 1, 2, 4, 5, 6, 8): Admin only has 6x2 For Lease dark.",
"6x4 stock For Sale white, Auction dark and white (pages 2, 4, 5, 6): no Admin version. Auction date only and plain: no Zander file.",
"8x4 For Sale stock and Coming Soon board: no Zander file.",
"A4 Landscape 2 page: side panel covers (pages 1, 2) and backs (pages 5, 6): no Admin template.",
"A4 4 page Landscape (all 6 pages): no Admin template.",
"A4 Portrait brochure: the Admin Parramatta AB brochure is a totally different layout, so no fair match.",
"A5 4 page Landscape (all pages): no A5 template in Admin Groups.",
"DL Just Listed pages 2 and 4, DL Just Sold pages 2, 3, 5, 6, 7 (testimonial and headshot versions), agent marketing DL (7 cards): no Admin version. 'ZZ Old' Just Sold file skipped as old.",
"A4 Tri Fold, A5 2 page, overlay stickers, A3 window card: no design file in the sheet.",
"No design showed a product name at the top, so matching used the sheet's product and variant names, plus size and layout."]
pg=comb.new_page(width=595,height=842); y=50
def line(t,fs=8.5,fn="helv",gap=3):
    global pg,y
    nl=int(pymupdf.get_text_length(t,fn,fs)/500)+1; h=nl*fs*1.3+gap
    if y+h>810: pg=comb.new_page(width=595,height=842); y=50
    pg.insert_textbox(pymupdf.Rect(40,y,555,y+h+8),t,fontsize=fs,fontname=fn); y+=h
line("Stone template check v2: summary",15,"hebo",8)
line("Designs from the Stone-Templates-Plan sheet (Zander files), checked against the Beleef Admin Groups templates.",8,"heit",6)
for fn,pgs,notes in summary:
    for P in pgs:
        line(P['title'],10.5,"hebo",2); line("Admin: "+P['matched'],8,"heit",2)
        for t,n,txt in notes:
            if t==P['title']: line(f"{n}. {txt}")
        y+=4
line("Not compared",10.5,"hebo",2)
for t in notcomp: line(t)
comb.save(OUT+"Stone-template-markup-v2.pdf",garbage=3,deflate=True)
print("pages",comb.page_count)
