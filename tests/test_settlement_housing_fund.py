from bs4 import BeautifulSoup

from scrapers import settlement_housing_fund as shf


def test_extract_waiting_list_items_and_parse():
    html = """
    <html>
      <body>
        <h5>New Lotteries and Re-rentals Managed by Settlement Housing Fund</h5>
        <p>Waiting List/Re-rentals</p>
        <ul>
          <li>Emerson: 203 Legend Drive, Sleepy Hollow, NY 10591 | <a href="https://bit.ly/EmersonApplication">https://bit.ly/EmersonApplication</a></li>
          <li>Sawyer Place: 50 Nepperhan Street and 45 Main Street, Yonkers, NY 10701 | <a href="https://bit.ly/SawyerPlaceApplication">https://bit.ly/SawyerPlaceApplication</a></li>
          <li>3333 Broadway| <a href="https://bit.ly/3333BroadwayApplication">https://bit.ly/3333BroadwayApplication</a></li>
        </ul>
        <h5>To request a status update on any past affordable housing lotteries currently managed by Settlement Housing Fund</h5>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    items = shf._extract_waiting_list_items(soup)

    assert len(items) == 3

    parsed = [shf._parse_listing(li) for li in items]
    assert all(p is not None for p in parsed)
    parsed = [p for p in parsed if p]

    assert parsed[0]["title"] == "Emerson: 203 Legend Drive, Sleepy Hollow, NY 10591"
    assert parsed[0]["excerpt"] is None
    assert parsed[0]["url"] == "https://bit.ly/EmersonApplication"
    assert parsed[0]["website_url"] == "https://www.settlementhousingfund.org/find-housing/"
    assert parsed[0]["canonical_id"].startswith("shf:")

    assert parsed[2]["title"] == "3333 Broadway"
    assert parsed[2]["excerpt"] is None
    assert parsed[2]["url"] == "https://bit.ly/3333BroadwayApplication"


def test_scrape_uses_only_waiting_list_section(monkeypatch):
    html = """
    <html>
      <body>
        <p>Waiting List/Re-rentals</p>
        <ul>
          <li>Emerson: 203 Legend Drive, Sleepy Hollow, NY 10591 | <a href="https://bit.ly/EmersonApplication">Apply</a></li>
        </ul>
        <h5>To request a status update on any past affordable housing lotteries currently managed by Settlement Housing Fund</h5>
        <ul>
          <li>Twin Parks Terrace</li>
        </ul>
      </body>
    </html>
    """

    class DummyResponse:
        text = html

        def raise_for_status(self):
            return None

    monkeypatch.setattr(shf.requests, "get", lambda *args, **kwargs: DummyResponse())
    listings = shf.scrape()

    assert len(listings) == 1
    assert listings[0]["title"] == "Emerson: 203 Legend Drive, Sleepy Hollow, NY 10591"
