import pytest
from SlidingWindowMap import SlidingWindowMap

@pytest.fixture
def mock_filled_map():
    map = SlidingWindowMap(3)
    test_pairs = [
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    ]
    for p in test_pairs:
        map.put(p[0], p[1])
    return map


def test_add_max_to_empty_all_unique():
    map = SlidingWindowMap(3)
    test_pairs = [
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    }
    for p in test_pairs:
        didPut = map.put(p[0], p[1])
        assert didPut, "pair not added successfully"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]


def test_add_max_to_empty_one_unique():
    map = SlidingWindowMap(3)
    test_pairs = [
        ("key1", "val1"),
        ("key1", "val1"),
        ("key1", "val1")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key1", "val1")
    }

    for i, p in enumerate(test_pairs):
        didPut = map.put(p[0], p[1])
        if i == 0:        # first insert should be successful
            assert didPut, "pair not added successfully"
        else:     # following inserts should not be successful
            assert not didPut, "pair should not have been added"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]


# "pushing out" one old pair with a new one
def test_add_one_most_recent_all_unique(mock_filled_map):
    map = mock_filled_map
    new_pairs = [
        ("key4", "val4")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key2", "val2"),
        ("key3", "val3"),
        ("key4", "val4")
    }

    for p in new_pairs:
        didPut = map.put(p[0], p[1])
        assert didPut, "pair not added successfully"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]


def test_add_one_most_recent_not_unique(mock_filled_map):
    map = mock_filled_map
    new_pairs = [
        ("key1", "val1")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    }

    for p in new_pairs:
        didPut = map.put(p[0], p[1])
        assert not didPut, "pair should not have been added"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]


# "pushing out" all old posts with new posts
def test_add_all_most_recent_all_unique(mock_filled_map):
    map = mock_filled_map
    new_pairs = [
        ("key4", "val4"),
        ("key5", "val5"),
        ("key6", "val6")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key4", "val4"),
        ("key5", "val5"),
        ("key6", "val6")
    }
    for p in new_pairs:
        didPut = map.put(p[0], p[1])
        assert didPut, "pair not added successfully"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]


# adding the same pairs
def test_add_all_most_recent_none_unique(mock_filled_map):
    map = mock_filled_map
    new_pairs = [
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    ]
    # SlidingWindowMap doesn't guarantee ordering
    exp_pairs = {
        ("key1", "val1"),
        ("key2", "val2"),
        ("key3", "val3")
    }
    for p in new_pairs:
        didPut = map.put(p[0], p[1])
        assert not didPut, "pair should not have been added"

    for p in exp_pairs:
        assert map.get(p[0]) == p[1]