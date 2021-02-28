import scrape
import pytest
from SlidingWindowMap import SlidingWindowMap


@pytest.fixture
def mock_post_titles():
    return {
        "[USA-WI] [H] bullshit and more crap [W] moolah",
        "[USA-WI] [H] 1060[W] moolah",
        "[USA-WI] [H] 1060 and crap[W] moolah",
        "[USA-WI] [H] crap and a maybe a gpu[W] moolah",
        "[USA-WI] [H] 1060[W] moolah and a 1060",
        "[USA-WI] [H] literally nothing [W] moolah "
    }


@pytest.fixture
def mock_post_body():
    return {
        "I have a 1060 but its not a gpu and $1060 dollars",
        "I have a GTX1060 6gb",
        "I have a 1060 6gb",
        "I have a gtx 1060-6gb",
        "I might have a gtx1060",
        "this shouldn't match anything"
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


def test_regex_filter_coarse(mock_post_titles, mock_most_recent_posts):
    compiled = scrape.compile_re(scrape.coarse_regex)
    scrape.most_recent_posts = mock_most_recent_posts
    posts_matched = scrape.regex_filter(mock_post_titles, compiled)

    assert len(posts_matched) == 5


def test_regex_filter_fine(mock_post_titles, mock_most_recent_posts):
    compiled = scrape.compile_re(scrape.coarse_regex)
    scrape.most_recent_posts = mock_most_recent_posts
    posts_matched = scrape.regex_filter(mock_post_titles, compiled)

    assert len(posts_matched) == 5
