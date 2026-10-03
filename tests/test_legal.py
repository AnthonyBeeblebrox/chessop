"""The legal notice, the privacy notice and the audience statistics (public spec §10, §12, G3),
driven through the hosted app as a browser would. What the statistics script does in a browser
is read from the script itself: there is no browser automation (ADR 0004)."""

import html
import re
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.hosted import CONTROLLER
from test_hosted import HOSTED, Site
from test_wire import E4_E5

CONTACT = '<a href="mailto:contact@chessop.fr">contact@chessop.fr</a>'


def text(page: str) -> str:
    """The words of the page's `<main>`, tags gone and spaces collapsed."""
    main = page[page.index("<main") :]
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", main)))


def test_the_legal_notice_names_only_the_host_and_gives_the_contact_and_the_terms(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        response = browser.get("/legal")
    assert response.status_code == 200
    page = response.text
    words = text(page)
    assert "OVH SAS, 2 rue Kellermann, 59100 Roubaix, France" in words
    assert "+33 9 72 10 10 07" in words
    assert "identity has been given to the host" in words
    assert "LCEN" in words
    assert CONTACT in page
    terms = re.search(r'<ul class="terms">(.*?)</ul>', page, re.S)
    assert terms is not None
    assert len(re.findall(r"<li>", terms.group(1))) == 3
    assert "provided as is" in terms.group(1) and "no warranty" in terms.group(1)
    assert "change or end" in terms.group(1) and "scraping" in terms.group(1)
    french = re.search(r'<section lang="fr">(.*?)</section>', page, re.S)
    assert french is not None
    assert "Hébergeur" in french.group(1) and "identité" in french.group(1)
    assert "OVH SAS" in french.group(1) and CONTACT in french.group(1)
    assert '<meta name="robots" content="noindex">' in page


# The processings the privacy notice has one entry each for (public spec §10), with the legal
# basis each names.
PROCESSINGS = {
    "email-accounts": "contract",
    "lichess-accounts": "contract",
    "signed-in-history": "contract",
    "anonymous-history": "contract",
    "refitting-and-counting": "legitimate interest",
    "error-logs": "legitimate interest",
    "audience-statistics": "legitimate interest",
    "ko-fi": "Ko-fi",
}


def test_the_privacy_notice_has_one_entry_per_processing_each_with_its_five_parts(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        response = browser.get("/privacy")
    assert response.status_code == 200
    page = response.text
    entries = dict(
        re.findall(r'<section class="processing" id="([a-z-]+)">(.*?)</section>', page, re.S)
    )
    assert list(entries) == list(PROCESSINGS)
    for name, basis in PROCESSINGS.items():
        entry = entries[name]
        parts = re.findall(r"<dt>([^<]+)</dt>", entry)
        if name == "ko-fi":  # its own controller: nothing of it reaches chessop
            assert "No donor data reaches chessop" in text("<main>" + entry)
            continue
        assert parts == ["Why", "Legal basis", "What", "Who receives it", "How long"], name
        assert basis in entry, name


def test_the_privacy_notice_names_the_controller_recipients_cookie_rights_and_retention(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        page = browser.get("/privacy").text
    words = text(page)
    assert CONTROLLER in words and "[" not in CONTROLLER  # the real name, not the placeholder
    assert CONTACT in page
    for recipient in ("OVH", "Scaleway", "Lichess", "GoatCounter", "UptimeRobot"):
        assert recipient in words, recipient
    assert "outside the EU" in words
    cookie = re.search(r'<section id="cookie">(.*?)</section>', page, re.S)
    assert cookie is not None and "one cookie" in cookie.group(1)
    assert "chessop" in cookie.group(1) and "12 months" in cookie.group(1)
    rights = text("<main>" + page[page.index('id="rights"') :]).lower()
    for right in ("access", "export", "correct", "erase", "restrict", "object"):
        assert right in rights, right
    assert "CNIL" in words and "after your death" in words and "within one month" in words
    assert "backups within 30 days" in words
    for period in ("12 months", "30 days", "fewer than 5 rounds", "24 months", "23 months"):
        assert period in words, period
    assert "Lichess accounts get no warning" in words
    assert "760 days" in words and "6 months" in words
    assert '<a href="/data">' in page
    assert '<meta name="robots" content="noindex">' in page


def test_the_privacy_notice_holds_the_audience_statistics_toggle(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        page = browser.get("/privacy").text
    entry = page[page.index('id="audience-statistics"') :]
    toggle = re.search(r'<input type="checkbox" id="count-me"[^>]*>', entry)
    assert toggle is not None
    assert '<script src="/static/audience-toggle.js" defer></script>' in page


def script(browser: TestClient, path: str) -> str:
    """The static script at `path`, as the browser gets it."""
    response = browser.get(path)
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    return response.text


def test_the_toggle_sets_and_clears_the_opt_out_flag_and_names_dnt_and_gpc(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        toggle = script(browser, "/static/audience-toggle.js")
    assert 'getElementById("count-me")' in toggle
    assert 'localStorage.setItem("skipgc", "t")' in toggle  # GoatCounter's own flag
    assert 'localStorage.removeItem("skipgc")' in toggle
    assert "navigator.doNotTrack" in toggle and "navigator.globalPrivacyControl" in toggle


STATS = "https://stats.chessop.example"
SNIPPET = f'<script src="/static/audience.js" data-goatcounter="{STATS}/count" defer></script>'
PAGES = ("/", "/progress", "/settings", "/help", "/legal", "/privacy", "/data", "/signin")


def test_the_statistics_snippet_is_on_every_hosted_page_when_its_url_is_configured(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path, replace(HOSTED, goatcounter_url=STATS))
    with site.browser() as browser:
        for path in PAGES:
            assert SNIPPET in browser.get(path).text, path


def test_no_statistics_snippet_without_its_url_nor_in_local_mode(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        for path in PAGES:
            assert "audience.js" not in browser.get(path).text, path
    with TestClient(create_app(E4_E5)) as browser:
        for path in ("/", "/progress", "/settings", "/help"):
            assert "audience.js" not in browser.get(path).text, path


def test_the_statistics_script_counts_a_page_view_and_nothing_more(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        counting = script(browser, "/static/audience.js")
    # Do Not Track, Global Privacy Control and the toggle's flag each stop the count.
    assert 'navigator.doNotTrack === "1"' in counting
    assert "navigator.globalPrivacyControl === true" in counting
    assert 'localStorage.getItem("skipgc") === "t"' in counting
    # The path without its query (UTM parameters gone), the referrer cut to its host.
    assert "p: location.pathname" in counting and "location.search" not in counting
    assert "new URL(document.referrer).host" in counting
    # Page views only: no events, and never the cookie.
    assert "document.cookie" not in counting and "event" not in counting


def test_the_footer_links_resolve_on_every_hosted_page(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        for path in PAGES:
            page = browser.get(path).text
            footer = re.search(r'<footer class="site">(.*?)</footer>', page, re.S)
            assert footer is not None, path
            links = dict(re.findall(r'<a href="([^"]+)">([^<]+)</a>', footer.group(1)))
            assert list(links.values()) == [
                "Legal notice",
                "Privacy",
                "Your data",
                "Source",
                "Ko-fi",
            ]
            for href in links:
                if href.startswith("/"):
                    assert browser.get(href).status_code == 200, (path, href)
                else:
                    assert href.startswith("https://"), (path, href)


KOFI_LINE = (
    '<a href="https://ko-fi.com/chessop">Support chessop on Ko-fi</a>: tips pay for the server'
    " and the domain, and are not tax-deductible."
)


def test_hosted_progress_carries_the_ko_fi_line_and_local_progress_does_not(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        assert KOFI_LINE in browser.get("/progress").text
    with TestClient(create_app(E4_E5)) as browser:
        page = browser.get("/progress").text
        assert "Ko-fi" not in page and "ko-fi" not in page


def test_hosted_help_gives_the_contact_address_and_local_help_the_repository_only(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        page = browser.get("/help").text
    closing = re.search(r'<p class="page helppage closing">(.*?)</p>', page, re.S)
    assert closing is not None
    assert CONTACT in closing.group(1)
    assert '<a href="https://github.com/AnthonyBeeblebrox/chessop">' in closing.group(1)
    with TestClient(create_app(E4_E5)) as browser:
        page = browser.get("/help").text
    closing = re.search(r'<p class="page helppage closing">(.*?)</p>', page, re.S)
    assert closing is not None
    assert "mailto:" not in page and "contact@" not in page
    assert '<a href="https://github.com/AnthonyBeeblebrox/chessop">' in closing.group(1)


def test_the_contact_address_is_a_mail_link_on_legal_privacy_data_and_help(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        for path in ("/legal", "/privacy", "/data", "/help"):
            assert CONTACT in browser.get(path).text, path
