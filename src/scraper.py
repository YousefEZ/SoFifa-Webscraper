from __future__ import annotations

import csv
from time import sleep
from functools import cache
from typing import TypedDict, Dict, Tuple, List
import sys
import re
import urllib
import urllib.request

import bs4


BASE_URL = "https://sofifa.com"
LEAGUE_NUMBER = 13
HEADERS = {"User-Agent": "Mozilla/5.0"}


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


class SeasonRecord(TypedDict, total=False):
    season: str
    player: Player
    team: Team


class Player:
    def __init__(self, name: str, identifier: str):
        self._name = name
        self._identifier = identifier
        self._seasons = self._get_all_statistics()

    def _get_all_statistics(self) -> Dict[str, SeasonRecord]:
        url = f"{BASE_URL}/player/{self._identifier}/live&set=true"
        soup = get_bs4(url)
        seasons = list(soup.find("table").find_all("tr"))
        return dict(self._create_record(seasons[i]) for i in range(2, len(seasons)))

    def _has_title(self, column: bs4.element.tag) -> bool:
        return column.has_attr("title") and column.string is not None

    def _extract_data(self, record: bs4.element.tag) -> Tuple[str, str]:
        return record.get("title").lower(), record.string

    def _extract_team(self, records: bs4.ResultSet) -> Team:
        try:
            team_number = extract_team_from_href(records[1].find("a").get("href"))
        except ValueError:
            team_number = "-"  # some teams don't have identifiers, in this case filling it with "-"
        return Team(records[1].get("title").strip(), team_number)

    def _extract_season(self, records: bs4.ResultSet) -> str:
        raw_season = records[0].string
        match = re.match(r'\d{4}/(\d{4})|\d{4}', raw_season)
    
        if match:
            season = match.group(1) if match.group(1) else match.group(0)
            return season[2:]
        raise ValueError("Season Number not detected")        

    def _create_record(self, season_data: bs4.element.tag) -> Tuple[str, SeasonRecord]:
        records = season_data.find_all("td")

        record: SeasonRecord = SeasonRecord(
            season=self._extract_season(records),
            player=self,
            team=self._extract_team(records),
            **dict(
                self._extract_data(record)
                for record in filter(self._has_title, records)
            ),
        )
        return record["season"], record

    def statistics(self, season: str) -> SeasonRecord:
        return self._seasons[season]

    def __str__(self) -> str:
        return str(self._identifier)


class Team:
    def __init__(self, name: str, identifier: str):
        self._name = name
        self._identifier = identifier

    def _extract_player_mapping(self, raw_player_data: List[str]) -> Tuple[str, Player]:
        PLAYER_NAME_INDEX = 3
        LINK_INDEX = 1
        extraction = list(list(raw_player_data)[PLAYER_NAME_INDEX])[1]
        pattern = r"/player/(\d+)/\S+/(\d+)"
        match = re.search(pattern, extraction.get("href"))

        if not match:
            raise ValueError(
                f"Could not find the player identifier for tag: {extraction}"
            )

        player_number = str(match.group(1))
        return extraction.string, Player(extraction.string, player_number)

    @cache
    def players(self, season: str) -> Dict[str, Player]:
        url = f"{BASE_URL}/players?tm={self._identifier}"
        soup = get_bs4(url)
        players = list(soup.find_all("tr"))
        return dict(
            self._extract_player_mapping(players[i]) for i in range(2, len(players))
        )

    def __str__(self) -> str:
        return self._identifier


class Season:
    def __init__(self, season: str):
        self._season: str = season
        self._week: str = 1
        self._league: str = 13
        self._teams: Dict[str, Team] = self._get_teams()

    @property
    def team_names(self) -> List[str]:
        return list(self._teams.keys())

    @property
    def teams(self) -> Dict[str, Team]:
        return self._teams

    def _extract_team_mapping(self, raw_team_data: List[str]) -> Tuple[str, str]:
        TEAM_NAME_INDEX = 3
        LINK_INDEX = 1
        extraction = list(list(raw_team_data)[TEAM_NAME_INDEX])[1]
        return extraction.string, Team(
            extraction.string, extract_team_from_href(extraction.get("href"))
        )

    def _get_teams(self) -> Dict[str, Team]:
        url = f"{BASE_URL}/teams?type=all&lg={LEAGUE_NUMBER}&r={self._season}00{self._week}&set=true"
        soup = get_bs4(url)
        teams = list(soup.find_all("tr"))
        return dict(self._extract_team_mapping(teams[i]) for i in range(2, len(teams)))

    @property
    def season_query(self) -> str:
        return f"{season}00{self._week}"

    def create_url(self) -> str:
        return f"{BASE_URL}/?r={self.season_query}&set=true"


fields = ['season', 'player', 'team', 'appearances', 'lineups', 'substitute in', 'substitute out', 'subs on bench', 'injuries', 'minutes played', 'goals', 'assists', 'big chances created', 'big chances missed', 'shots', 'on target', 'shots blocked', 'hit woodwork', 'passes', 'accurate passes', 'key passes', 'crosses', 'crosses accurate', 'long balls', 'through balls', 'passing accuracy', 'dribbles attempts', 'dribbles success', 'dribbled past', 'dribbles dispossessed', 'duels', 'duels won', 'tackles', 'interceptions', 'blocks', 'long balls won', 'aerials won', 'clearances', 'fouls committed', 'fouls drawn', 'yellow cards', '2nd yellow card', 'red cards', 'offsides', 'saves', 'inside box saves', 'penalty saved', 'clean sheets', 'conceded', 'rating']

if __name__ == "__main__":
    season = Season("23")
    with open("2023.csv", 'w') as season_file:
        season_writer = csv.DictWriter(season_file, delimiter=",", fieldnames=fields) 
        for team in season.teams.values():
            for player in team.players("23").values():
                try:
                    record = player.statistics("23")
                except KeyError:
                    print("Unable to retrieve 23 for: ", player)
                else:
                    season_writer.writerow(record)


