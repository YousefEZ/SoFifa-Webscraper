from __future__ import annotations

from time import sleep
from functools import cache
from typing import Any, TypedDict, Dict, Tuple, List, cast
import re
from typing_extensions import Required
import urllib
import urllib.request
import urllib.error

import bs4
import bs4.element

BASE_URL = "https://sofifa.com"
LEAGUE_NUMBER = "13"  # EPL
WEEK_NUMBER = "01"
HEADERS = {"User-Agent": "Mozilla/5.0"}

FIELDS = [
    "season",
    "player",
    "team",
    "appearances",
    "lineups",
    "substitute in",
    "substitute out",
    "subs on bench",
    "injuries",
    "minutes played",
    "goals",
    "assists",
    "big chances created",
    "big chances missed",
    "shots",
    "on target",
    "shots blocked",
    "hit woodwork",
    "passes",
    "accurate passes",
    "key passes",
    "crosses",
    "crosses accurate",
    "long balls",
    "through balls",
    "passing accuracy",
    "dribbles attempts",
    "dribbles success",
    "dribbled past",
    "dribbles dispossessed",
    "duels",
    "duels won",
    "tackles",
    "interceptions",
    "blocks",
    "long balls won",
    "aerials won",
    "clearances",
    "fouls committed",
    "fouls drawn",
    "yellow cards",
    "2nd yellow card",
    "red cards",
    "offsides",
    "saves",
    "inside box saves",
    "penalty saved",
    "clean sheets",
    "conceded",
    "rating",
]


def get_bs4(url: str) -> bs4.BeautifulSoup:
    page_req = urllib.request.Request(url, headers=HEADERS)
    page = urllib.request.urlopen(page_req)
    return bs4.BeautifulSoup(page, "html.parser")


def extract_team_from_href(href: str) -> str:
    pattern = r"/team/(\d+)/\S+/"
    match = re.search(pattern, href)

    if not match:
        raise ValueError(f"could not find the team identifier for tag: {href}")

    return str(match.group(1))


def generate_season_query(season: str, week: str) -> str:
    return f"{season}00{week}"


def retry_from_header(func):
    DEFAULT_RETRY = 15  # seconds

    def decorator(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except urllib.error.HTTPError as e:
                if (
                    e.code != 429
                ):  # Check if the error is due to rate limiting (HTTP 429 Too Many Requests)
                    raise e
                retry_after = e.headers.get("Retry-After")
                sleep(float(retry_after) if retry_after else DEFAULT_RETRY)

    return decorator


class SeasonRecord(TypedDict, total=False):
    season: Required[str]
    player: Required[Player]
    team: Required[Team]


class Player:
    def __init__(self, name: str, identifier: str):
        self._name: str = name
        self._identifier: str = identifier

    @property
    def name(self) -> str:
        return self._name

    @cache
    @retry_from_header
    def statistics(self) -> Dict[str, SeasonRecord]:
        url = f"{BASE_URL}/player/{self._identifier}/live&set=true"
        soup = get_bs4(url)
        table = soup.find("table")
        assert type(table) == bs4.element.Tag, f"Table is not a tag: {table}"

        if not table:
            # this is the case if the player is new, example: https://sofifa.com/player/268550/joshua-feeney/live
            return dict()
        seasons = list(table.find_all("tr"))
        return dict(self._create_record(seasons[i]) for i in range(2, len(seasons)))

    def _has_title(self, column: bs4.element.Tag) -> bool:
        return column.has_attr("title") and column.string is not None

    def _extract_data(self, record: bs4.element.Tag) -> Tuple[str, str]:
        # some data starts with "-" but is followed by weird characters, so normalising

        title = record.get("title")
        assert type(title) == str, f"Title is not a string: {title}"

        assert record.string, f"Record has no string: {record}"
        value = record.string[0]
        assert type(value) == str, f"Value is not a string: {value}"

        return title.lower(), value

    def _extract_team(self, records: bs4.ResultSet, season: str) -> Team:
        try:
            team_number = extract_team_from_href(records[1].find("a").get("href"))
        except ValueError:
            team_number = "-"  # some teams don't have identifiers, in this case filling it with "-"
        return Team(records[1].get("title").strip(), team_number, season, WEEK_NUMBER)

    def _extract_season(self, records: bs4.ResultSet) -> str:
        raw_season = records[0].string
        match = re.match(r"\d{4}/(\d{4})|\d{4}", raw_season)

        if match:
            season = match.group(1) if match.group(1) else match.group(0)
            return season[2:]
        raise ValueError("Season Number not detected")

    def _create_record(self, season_data: bs4.element.Tag) -> Tuple[str, SeasonRecord]:
        records = season_data.find_all("td")
        season: str = self._extract_season(records)

        record: SeasonRecord = SeasonRecord(
            season=season,
            player=self,
            team=self._extract_team(records, season),
            **dict(
                self._extract_data(record)
                for record in filter(self._has_title, records)
            ),
        )
        return record["season"], record

    @cache
    def season_record(self, season: str) -> SeasonRecord:
        return self.statistics()[season]

    def __str__(self) -> str:
        return str(self._identifier)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Player):
            return other._identifier == self._identifier
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self._identifier)


class Team:
    def __init__(self, name: str, identifier: str, season: str, week: str):
        self._name = name
        self._identifier = identifier
        self._season = season
        self._week = week

    def _extract_player_mapping(
        self, raw_player_data: bs4.element.Tag
    ) -> Tuple[str, Player]:
        PLAYER_NAME_INDEX = 3
        raw_player = cast(bs4.element.Tag, list(raw_player_data)[PLAYER_NAME_INDEX])
        extraction = cast(bs4.element.Tag, list(raw_player)[1])

        player_url = extraction.get("href")
        assert type(player_url) == str, f"Player number is not a string: {player_url}"

        pattern = r"/player/(\d+)/\S+/(\d+)"
        match = re.search(pattern, player_url)

        if not match:
            raise ValueError(
                f"Could not find the player identifier for tag: {extraction}"
            )

        player_number = str(match.group(1))

        player_name = extraction.string
        assert player_name, f"Player name is empty: {player_name}"

        return player_name, Player(player_name, player_number)

    @cache
    @retry_from_header
    def players(self) -> Dict[str, Player]:
        url = f"{BASE_URL}/players?tm={self._identifier}&r={generate_season_query(self._season, self._week)}&set=true"
        soup = get_bs4(url)
        players = list(soup.find_all("tr"))
        return dict(
            self._extract_player_mapping(players[i]) for i in range(2, len(players))
        )

    def __str__(self) -> str:
        return str(self._name).strip()


class Season:
    def __init__(
        self, season: str, week: str = WEEK_NUMBER, league: str = LEAGUE_NUMBER
    ):
        self._season: str = season
        self._week: str = week
        self._league: str = league
        self._teams: Dict[str, Team] = self._get_teams()

    @property
    def team_names(self) -> List[str]:
        return list(self._teams.keys())

    @property
    def teams(self) -> Dict[str, Team]:
        return self._teams

    def _extract_team_mapping(self, raw_team_data: bs4.element.Tag) -> Tuple[str, Team]:
        TEAM_NAME_INDEX = 3
        raw_team = cast(bs4.element.Tag, list(raw_team_data)[TEAM_NAME_INDEX])
        raw_team_name: bs4.element.Tag = cast(bs4.element.Tag, list(raw_team)[1])

        team_name = raw_team_name.string
        assert team_name, f"Team name is empty: {team_name}"

        team_number = raw_team_name.get("href")
        assert type(team_number) == str, f"Team number is empty: {team_number}"

        return team_name, Team(
            team_name, extract_team_from_href(team_number), self._season, self._week
        )

    @retry_from_header
    def _get_teams(self) -> Dict[str, Team]:
        url = f"{BASE_URL}/teams?type=all&lg={LEAGUE_NUMBER}&r={self._season}00{self._week}&set=true"
        soup = get_bs4(url)
        teams: list[bs4.element.Tag] = list(soup.find_all("tr"))
        return dict(self._extract_team_mapping(teams[i]) for i in range(2, len(teams)))

    def create_url(self) -> str:
        return (
            f"{BASE_URL}/?r={generate_season_query(self._season, self._week)}&set=true"
        )
