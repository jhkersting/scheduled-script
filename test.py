import datetime

with open('2022-senate/update-time.txt', 'w') as f:
    f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
