import re
from difflib import SequenceMatcher
def tokenize(s): return set(re.findall(r"[a-z0-9]+",s.lower()))
def lexical_similarity(a,b):
    ta,tb=tokenize(a),tokenize(b); jac=len(ta&tb)/len(ta|tb) if ta|tb else 0.0; char=SequenceMatcher(None,a.lower(),b.lower()).ratio(); return 0.65*jac+0.35*char
def candidate_score(source_label,target_label,source_depth,target_depth):
    label=lexical_similarity(source_label,target_label); depth=max(0.0,1.0-abs(source_depth-target_depth)/4.0); return round(0.88*label+0.12*depth,6)
def ranking_band(score):
    return 'strong_candidate' if score>=0.75 else 'moderate_candidate' if score>=0.58 else 'weak_candidate' if score>=0.42 else 'very_weak_candidate'
