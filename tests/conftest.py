import pytest

# Hand-written synthetic IVTFF snippet (NOT third-party data) exercising every construct.
SAMPLE = """\
#=IVTFF Eva- 2.0 M 5
# synthetic test file
#
<f1r>      <! $Q=A $P=A $F=a $B=1 $I=T $L=A $H=1 $C=1 $X=V>
# page 1
<f1r.1,@P0>       <%>fachys.ykal.ar<!strange r>.ataiin.shol.shory.[cth:oto]res.y.kor
<f1r.2,+P0>       sory.ckhar.or,y.kair.{c'y}.dai[{cto}:@194;]y.d?n
<f1r.3,=Pt>       ydaraishy<$>
<f1r.4,*P0>       <%><!@252;>odar.@130;chy.???.qol<->daiin.ok<~>ar
<f1r.5,!P0>       shouldnotexist
<f1r.6,+P0>       aaa.bbb.ccc.ddd.eee /
/ fff.ggg
#
<f1v>      <! $Q=A $P=B $F=a $B=1 $I=H $L=@ $H=@ $C=1>
<f1v.1,@Lp>       daiin
<f1v.2,@P0>       <@L=B><@H=2>chedy.qokedy
<f1v.3,+P0>       shedy.qokeedy
<f1v.4,+Lx>       latin
<f1v.5,+P0>       <@L=@>qokain.chedy
"""


@pytest.fixture(scope="session")
def sample_text():
    return SAMPLE


@pytest.fixture(scope="session")
def sample_corpus():
    from msdecipher.ivtff import parse_lines
    return parse_lines(SAMPLE.splitlines(), "sample")
