import pandas as pd
from pathlib import Path
path = Path('../data/adxl355').resolve()

files = [str(file) for file in path.glob('*.csv')]

cnt = 0
val = 0
for file in files:
    df = pd.read_csv(file)

    ts = [df.columns[3]]
    ts.extend(df[df.columns[3]])
    
    idx = 0 
    for t in ts:
        cnt += 1
        if idx == 2999:
            break
        val += float(ts[idx+1]) - float(ts[idx])
        idx +=1 

print(val / cnt)
