import csv
from typing import Set

from rich.console import Console
from rich.progress import TaskID, TextColumn, BarColumn, SpinnerColumn, Progress, track

import fifascraper


def progress_bar(func):
    def decorator(*args, **kwargs):
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.fields[team]}"),
            transient=True,
        ) as progress:
            return func(progress, *args, **kwargs)

    return decorator


def write_players(players, writer) -> None:
    for player in players:
        try:
            record = player.season_record("23")
        except KeyError:
            # new player, does not have a record
            continue
        else:
            writer.writerow(record)


@progress_bar
def scrape(progress):
    season = fifascraper.Season("23")
    with open("2023.csv", "w") as season_file:
        season_writer = csv.DictWriter(
            season_file, delimiter=",", fieldnames=fifascraper.FIELDS
        )
        teams_progress = progress.add_task(
            "[green] Loading Team Statistics for Season 23",
            total=len(season.teams),
            team="-",
        )

        for team_name, team in season.teams.items():
            write_players(team.players("23").values(), season_writer)
            progress.update(teams_progress, advance=1, team=team_name)
            progress.refresh()


def set_of_players(season_number: str) -> Set[fifascraper.Player]:
    season = fifascraper.Season(season_number)
    players = set().union(
        *map(lambda team: team.players("23").values(), season.teams.values())
    )
    return players


def scrape_players():
    seasons = list(map(lambda num: num.zfill(2), map(str, range(7, 24))))
    players = set().union(*map(set_of_players, track(seasons, "Fetch Players")))
    with open("players.csv", "w") as season_file:
        season_writer = csv.DictWriter(
            season_file, delimiter=",", fieldnames=fifascraper.FIELDS
        )
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.fields[player]}"),
        ) as progress:
            player_progress = progress.add_task(
                "[green] Loading Player Statistics All-Time",
                total=len(players),
                player="-",
            )
            for player in players:
                progress.update(player_progress, advance=0, player=player.name)
                progress.refresh()
                try:
                    records = player.statistics()
                except KeyError:
                    continue
                else:
                    for record in records.values():
                        season_writer.writerow(record)
                    progress.update(player_progress, advance=1, player=player.name)
                    progress.refresh()


if __name__ == "__main__":
    players = scrape_players()
