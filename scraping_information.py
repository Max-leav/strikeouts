headers = {
  'sec-ch-ua-platform': '"Windows"',
  'Referer': 'https://www.fangraphs.com/players/eury-perez/27768/stats/pitching',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/133.0.0.0 (Edition std-1)',
  'sec-ch-ua': '"Opera GX";v="133", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0'
}

fg_PitchersBaseUrl = "https://www.fangraphs.com/_next/data/Srtn7z-JINs_4qWLRn9y2/players/eury-perez/27768/stats/pitching.json?playerNameRoute=eury-perez&playerId=27768"

class Pitcher:
    def __init__(self, firstName, lastName):
        self.fName = firstName
        self.lName = lastName
        self.playerId = getPlayerId(firstName, lastName)
        self.url = f"https://www.fangraphs.com/_next/data/Srtn7z-JINs_4qWLRn9y2/players/{firstName}-{lastName}/{self.playerId}/stats/pitching.json?playerNameRoute={firstName}-{lastName}&playerId={self.playerId}"
  
class Batter:
    def __init__(self, firstName, lastName):
        self.fName = firstName
        self.lName = lastName
        self.playerId = getPlayerId(firstName, lastName)
        self.url = f"https://www.fangraphs.com/_next/data/qzBSEHXDTj0Ut4UbaRB2T/players/{firstName}-{lastName}/{self.playerId}/splits.json?position=NP&playerNameRoute={firstName}-{lastName}&playerId={self.playerId}"
  

