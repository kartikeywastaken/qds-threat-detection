import pytest
from math_model.min_entropy_bounds import min_entropy_rate, forgery_bound, chsh_entropy

def test_math():
    values = [forgery_bound(n, .04) for n in (8,16,32,64)]
    print('Forgery bounds n=8,16,32,64:', values)
    assert all(a>b for a,b in zip(values,values[1:]))
    assert min_entropy_rate(0)==1 and min_entropy_rate(.5)==0
    assert chsh_entropy(2)==0
    with pytest.raises(ValueError): min_entropy_rate(-.1)
