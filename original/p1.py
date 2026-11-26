import sys; sys.path.insert(0,'stc2'); from comp import *
Z="stone-sheet-designs/stock-6x4/342117, 356427 Generic_Signboard 4x6 Edgewrap Portrait.pdf"; ZT=(67.3,67.3,931.9,1365.6)
T="stone-group-templates/central-coast/6x4 portrait.pdf"; TT=(157.3,128.98,3556.1,5228.5)
show(T,0,TT,"TEMPLATE")
for pn in (0,2): show(Z,pn,ZT,"ZANDER")
t=render(T,0,TT); pb(t,"T")
for pn in (0,2):
    a=render(Z,pn,ZT); pb(a,f"Z p{pn+1}")
side([t,render(Z,0,ZT),render(Z,2,ZT)],"stc2/w/s6x4.png")
