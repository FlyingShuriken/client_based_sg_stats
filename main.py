from lcu_driver import Connector
from pprint import pprint
import json
from requests import get
import webbrowser
connector = Connector()


@connector.ready
async def connect(connection):
    print('LCU API is ready to be used.')
    user = await connection.request("get", "/lol-summoner/v1/current-summoner")
    user_json = await user.json()
    name = user_json["displayName"]
    print(f"Name: {name}")
    with open("team.js", "w") as file:
        file.write("data = {}")

    res = get("https://ddragon.leagueoflegends.com/api/versions.json")
    text = res.text
    patch = (json.loads(text))[0]

    res = get(
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/data/en_US/champion.json")
    text = json.loads(res.text)

    champion_list = {}
    for i in text["data"]:
        champion_list[text["data"][i]['key']] = text["data"][i]['id']
    open("champion.json", "w").write(str(champion_list).replace("'", '"'))
    print(f"UPDATED TO PATCH {text['version']}")


@connector.ws.register('/lol-champ-select/v1/session', event_types=('UPDATE',))
async def found_match(connection, event):
    myTeam = event.data["myTeam"]
    data = {}
    for i in myTeam:
        id = i['summonerId']
        if id != 0:
            req = await connection.request("get", f"/lol-summoner/v1/summoners/{id}")
            res = await req.json()
            puuid = res["puuid"]
            name = res["displayName"]
            lvl = res["summonerLevel"]
            version = (json.loads(
                get("https://ddragon.leagueoflegends.com/realms/kr.json").text))["v"]
            data[id] = {
                "name": name,
                "puuid": puuid,
                "lvl": lvl,
                "version": version,
                "rank": {},
                "games": {}
            }

            rank_req = await connection.request("get", f"/lol-ranked/v1/ranked-stats/{puuid}")
            rank_res = await rank_req.json()

            for ii in rank_res["queues"]:
                data[id]["rank"][ii['queueType']
                                 ] = f"{ii['tier']} {ii['division']} {ii['leaguePoints']}LP - {ii['wins']} WINS"

            get_id = get(
                f"https://acs-garena.leagueoflegends.com/v1/players?name={name}&region=SG")
            ids = json.loads(get_id.text)["accountId"]
            get_history = get(
                f"https://acs-garena.leagueoflegends.com/v1/stats/player_history/SG/{ids}?begIndex=0&endIndex=10&")
            histories = json.loads(get_history.text)
            histories_list = histories['games']['games']
            histories_list.reverse()

            with open("champion.json", "r") as file:
                champion_list = json.load(file)
            loops = 1
            for i in histories_list:
                champion = champion_list[str(
                    i['participants'][0]['championId'])]
                kda = f"{i['participants'][0]['stats']['kills']}/{i['participants'][0]['stats']['deaths']}/{i['participants'][0]['stats']['assists']}"
                level = i['participants'][0]['stats']['champLevel']
                damage = i['participants'][0]['stats']['totalDamageDealtToChampions']
                win = i['participants'][0]['stats']['win']
                gold = i['participants'][0]['stats']['goldEarned']
                cs = i['participants'][0]['stats']['totalMinionsKilled']
                gameModeID = i['queueId']
                win_lose = ""
                gameModeIDS = {
                    420: "RANKED",
                    450: "ARAM",
                    430: "NORMAL"
                }
                gameMode = "Other"

                if gameModeID in gameModeIDS.keys():
                    gameMode = gameModeIDS[gameModeID]

                if win == True:
                    win_lose = "#ccff99"
                else:
                    win_lose = "#ff9999"

                data[id]["games"][loops] = {
                    "mode": gameMode,
                    "champion": champion,
                    "kda": kda,
                    "level": level,
                    "dmg": damage,
                    "win": win_lose,
                    "gold": gold,
                    "cs": cs
                }
                loops += 1

    with open("team.js", "r") as file:
        prev = file.read()

    up = f"data = {str(json.dumps(data))}"

    with open("team.js", "w") as file:
        if prev != up and prev != "":
            file.write(
                f"data = {str(json.dumps(data))}"
            )

            webbrowser.open("index.html", new=0)

connector.start()
