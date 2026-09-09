from regacct.framework.prudential.evaluator import evaluate_ast

def test_ratio():
    ast={'op':'div','left':{'op':'value','ref':'A'},'right':{'op':'value','ref':'B'}}
    assert evaluate_ast(ast,{'A':40,'B':100}).value==0.4

def test_missing_is_explicit():
    ast={'op':'add','left':{'op':'value','ref':'VQ10'},'right':{'op':'value','ref':'weight:VQ11'}}
    assert 'weight:VQ11' in evaluate_ast(ast,{'VQ10':10}).missing_inputs
