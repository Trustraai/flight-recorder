from flight_recorder.provenance import GENESIS_HASH, ProvenanceChain


def test_empty_chain_head_is_genesis():
    chain = ProvenanceChain()
    assert chain.head_hash == GENESIS_HASH


def test_append_links_hashes():
    chain = ProvenanceChain()
    e1 = chain.append({"a": 1})
    e2 = chain.append({"a": 2})
    assert e1.previous_hash == GENESIS_HASH
    assert e2.previous_hash == e1.record_hash


def test_verify_passes_when_untampered():
    chain = ProvenanceChain()
    for i in range(5):
        chain.append({"i": i})
    is_valid, break_index = chain.verify()
    assert is_valid is True
    assert break_index is None


def test_verify_detects_tampering():
    chain = ProvenanceChain()
    chain.append({"i": 0})
    chain.append({"i": 1})
    chain._entries[0].payload["i"] = 999
    is_valid, break_index = chain.verify()
    assert is_valid is False
    assert break_index == 0
