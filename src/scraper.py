from typing import Dict, List
from urllib.request import urlopen

from bs4 import BeautifulSoup


BASE_URL = "https://sofifa.com"
LEAGUE_NUMBER = 13

class Player:
	
	def __init__(self, name: str, number: int):
		self._name = name
		self._number = number



class Team:
	def __init__(self, name: str, number: int):
		self._name = name
		self._number = number

	def players(self, season: number) -> List[Player]:
		...

	def stats(self, season: number) -> List[int]:
		...


class SeasonScraper:

    def __init__(self, season: int):
        self._season = season
     	self._week = 1
		self._league = 13		 
		self._teams = self._get_teams()

	def _get_teams(self) -> Dict[str, Team]
		url = "https://sofifa.com/teams?type=all&lg={LEAGUE_NUMBER}&r={self._season}00{self._week}&set=true"
		page_response = urlopen(url)
		html = page_response.read().decode("utf-8")
		soup = BeautifulSoup(html, "html.parser")

	@property
	def season_query(self) -> str:
		return f"{season}00{self._week}" 

    def create_url(self) -> str:
		return f"{BASE_URL}/?r={self.season_query}&set=true"

	@property
	def teams(self) -> List[Team]:
		...

