import scrape
import pytest
from SlidingWindowMap import SlidingWindowMap


@pytest.fixture
def mock_post_titles():
    return {
        "[USA-WI] [H] bullshit and more crap [W] paypal",
        "[USA-WI] [H] 1060[W] PP",
        "[USA-WI] [W] 1060[H] PP",
        "[USA-WI] [H] crap and a maybe a gpu[W] moolah",
        "[USA-WI] [H] literally nothing [W] moolah ",
        "[USA - WI][H] GTX 1060 6gb[W] Paypal"
    }


@pytest.fixture
def mock_post_body():
    return {
        "I have $1060 dollars",
        "I have a GTX1060 6gb",
        "should not match anything because of title",
        "I have a gtx 1060-6gb",
        "this shouldn't match anything",
        "test fine regex"
    }

num_posts = 6

@pytest.fixture
def mock_most_recent_posts(mock_post_titles, mock_post_body):
    most_recent = SlidingWindowMap(num_posts)
    for title, body in zip(mock_post_titles, mock_post_body):
        most_recent.put(
            title,
            {
                'title': title,
                'body': body
             }
        )
    return most_recent


def test_regex_filter_title(mock_post_titles, mock_most_recent_posts):
    compiled = scrape.compile_re(scrape.title_regex)
    scrape.most_recent_posts = mock_most_recent_posts
    posts_matched = scrape.regex_filter(mock_post_titles, compiled)
    expected = {
        "[USA-WI] [H] bullshit and more crap [W] paypal",
        "[USA-WI] [H] 1060[W] PP",
        "[USA - WI][H] GTX 1060 6gb[W] Paypal"
    }

    assert posts_matched == expected


def test_regex_filter_fine(mock_post_titles, mock_most_recent_posts):
    compiled = scrape.compile_re(scrape.fine_regex)
    scrape.most_recent_posts = mock_most_recent_posts
    posts_matched = scrape.regex_filter(mock_post_titles, compiled)
    expected = {
        "[USA - WI][H] GTX 1060 6gb[W] Paypal"
    }

    assert posts_matched == expected
