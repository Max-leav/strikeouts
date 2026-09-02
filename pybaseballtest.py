from pybaseball import *

if __name__ == '__main__':
    data = statcast_batter('2026-04-01', '2026-04-30', player_id=660271)
    print(len(data))