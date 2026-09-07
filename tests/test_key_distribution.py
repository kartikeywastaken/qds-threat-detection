from qds_protocol.key_distribution import distribute

def test_distribution():
    assert distribute(64,7)==distribute(64,7)
    assert distribute(64,7).bits!=distribute(64,8).bits
