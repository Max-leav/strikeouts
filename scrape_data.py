from requests import get
from scraping_information import *
from datetime import datetime, date, timedelta
import json

def getAllGameIds():
    gameIds = {
        2024: [],
        2025: [],
        2026: []
    }
    
    
    for year in mlbDates.keys():
        dateFrom = date.fromisoformat(mlbDates[year][0])
        dateTo = date.fromisoformat(mlbDates[year][1])
        
        while dateFrom < dateTo:
            df = date.isoformat(dateFrom)
            print(df)
            data = get(getMlbScheduleUrl(df,df), headers=headers).json()["dates"]
            if len(data) > 0:
                data = data[0]["games"]
            
            gameIds[dateFrom.year].extend([d["gamePk"] for d in data])
            
            dateFrom = dateFrom + timedelta(days=1)
            
    file = open("mlbGameIds.json", "w")
    file.write(json.dumps(gameIds, indent=4))
    file.close()
        
    

def getProbablePitchers(date):
    pass

if __name__ == '__main__':
    getAllGameIds()