from __future__ import annotations

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


class SeasonRecord(TypedDict, total=False):
    season: str
    player: Player
    team: Team


class Player:
	
    def __init__(self, name: str, number: int):
        self._name = name
        self._number = number
        self._seasons = self._get_all_statistics()

    def _get_all_statistics(self) -> Dict[str, SeasonRecord]:
        url = f"{BASE_URL}/player/{self._number}/live&set=true"
        soup = get_bs4(url)
        seasons = list(soup.find("table").find_all("tr"))
        return dict(self._create_record("23", seasons[i]) for i in range(2, len(seasons)))

    def _has_title(self, column: bs4.element.tag) -> bool:
        return column.has_attr("title") and column.string is not None

    def _extract_data(self, record: bs4.element.tag) -> Tuple[str, str]:
        return record.get("title"), record.string 

    def _create_record(self, season: str, season_data: bs4.element.tag) -> Tuple[str, SeasonRecord]:
        records = season_data.find_all("td")
        record: SeasonRecord = {self._extract_data(record) for record in filter(self._has_title, records)}
        return season, record

    def statistics(self, season: str) -> SeasonRecord:
        return self._seasons[season]


class Team:

    def __init__(self, name: str, number: int):
        self._name = name
        self._number = number
   
    def _extract_player_mapping(self, raw_player_data: List[str]) -> Tuple[str, int]:
        PLAYER_NAME_INDEX = 3
        LINK_INDEX = 1
        extraction = list(list(raw_player_data)[PLAYER_NAME_INDEX])[1]
        pattern = r"/player/(\d+)/\S+/(\d+)"
        match = re.search(pattern, extraction.get("href"))

        if not match:
            raise ValueError(f"Could not find the player number for tag: {extraction}")

        player_number = int(match.group(1))
        return extraction.string, Player(extraction.string, player_number)

    @cache
    def players(self, season: int) -> List[Player]:
        url = f"{BASE_URL}/players?tm={self._number}"
        soup = get_bs4(url)
        players = list(soup.find_all("tr"))
        return dict(self._extract_player_mapping(players[i]) for i in range(2, len(players)))



class SeasonScraper:

    def __init__(self, season: int):
        self._season: int = season
        self._week: int = 1
        self._league: int = 13		 
        self._teams: Dict[str, Team] = self._get_teams()

    @property
    def teams(self) -> Dict[str, Team]:
        return self._teams

    def _extract_team_mapping(self, raw_team_data: List[str]) -> Tuple[str, int]:
        TEAM_NAME_INDEX = 3
        LINK_INDEX = 1
        extraction = list(list(raw_team_data)[TEAM_NAME_INDEX])[1]
        pattern = r"/team/(\d+)/\S+/"
        match = re.search(pattern, extraction.get("href"))

        if not match:
            raise ValueError(f"Could not find the team number for tag: {extraction}")

        team_number = int(match.group(1))
        return extraction.string, Team(extraction.string, team_number)

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


if __name__ == "__main__":
    season_scraper = SeasonScraper(23)
    teams = list(season_scraper.teams.values())
    players = list(teams[0].players(23).values())
    print(players)
    print(players[0].statistics("23"))
