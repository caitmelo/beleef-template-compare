import sys; sys.path.insert(0,'stc2'); from comp import *
Z="stone-sheet-designs/stock-6x2/342119_Signboard 6x2 Edgewrap Portrait.pdf"; ZT=(60.2,60.2,485.4,1357.1)
T="stone-group-templates/central-coast/6 x 2.pdf"; TT=(129.0,129.0,1826.9,5228.5)
show(T,0,TT,"TEMPLATE")
for pn in (2,6): show(Z,pn,ZT,"ZANDER")
t=render(T,0,TT,600); pb(t,"T")
for pn in (2,6): pb(render(Z,pn,ZT,600),f"Z p{pn+1}")
side([t,render(Z,2,ZT,600),render(Z,6,ZT,600)],"stc2/w/s6x2.png")
