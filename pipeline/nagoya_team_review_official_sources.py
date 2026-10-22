"""Official Nagoya ward PDF reference index for human team review.

The city designated indoor facilities list is published as CC BY 4.0 open data:
https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
Source listing stated as of 2026-09-01; retrieved and manually checked on
2026-10-22. This module contains ONLY city-published facility name/address,
ward labels and official municipal PDF URLs; no ABR/GSI coordinates or inferred
site, emergency suitability, actual opening, or entrance approvals.

This is a point-in-time SOURCE LINK INDEX, not a current-data verification
engine. Live source revisions must be assessed independently.
"""

OFFICIAL_INDEX_AS_OF = "2026-09-01"
OFFICIAL_INDEX_CHECKED_ON = "2026-10-22"
OFFICIAL_MAIN = "https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html"
OFFICIAL_LICENSE = "https://creativecommons.org/licenses/by/4.0/deed.ja"

# Every pair verified against the ward-specific original PDF and page screenshot.
# For every lookup, require both listed facility name AND listed address to match.
WARD_PDFS = {
    "天白区": "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai16tenpaku0809.pdf",
    "守山区": "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai13moriyama0809.pdf",
    "緑区": "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai14midori0806.pdf",
    "東区": "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai02higashi0809.pdf",
    "中村区": "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai05nakamura0804.pdf",
}

OFFICIAL_NAME_ADDRESS_WARD = {
    ("平針南小学校", "平針南4-402"): "天白区",
    ("平針南コミュニティセンター", "平針南1-113"): "天白区",
    ("平針小学校", "向が丘1-620"): "天白区",
    ("大森小学校", "大森4-401"): "守山区",
    ("大森中学校", "大森1-2601"): "守山区",
    ("大森コミュニティセンター", "大森4-206-1"): "守山区",
    ("鳴海コミュニティセンター", "鳴海町字城22-1"): "緑区",
    ("東桜小学校", "東桜1-13-1"): "東区",
    ("名城大学附属高等学校", "新富町1-3-16"): "中村区",
}


def official_ward_pdf(name: str, address: str) -> dict | None:
    """Find only a wholly matching official, point-in-time listed record."""
    ward = OFFICIAL_NAME_ADDRESS_WARD.get((name, address))
    if not ward:
        return None
    return {
        "title": (
            f"名古屋市・{ward} 屋内指定施設一覧（2026-09-01時点、CC BY 4.0）"
        ),
        "url": WARD_PDFS[ward],
    }
