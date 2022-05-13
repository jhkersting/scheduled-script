import pandas as pd
from scipy.stats import t
import numpy as np
import math
import random
import time
from dateutil import parser
import datetime as dtime
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
print("GEN BALLOT")
# STARTING VARIABLES #
start_time = time.time()
#start_date = dtime.datetime(2021, 4, 1)  # RERUN ALL SIMULATIONS
start_date = dtime.datetime.now()  # RUN TODAY SIMULATIONS
election_date = dtime.datetime(2021, 11, 3)


def assign_weight(n, days, g, v, internal, dfe):
    n = 200 if n == "" else n
    n_weight = 55.22 if n > 3500 else 5 / (1 / math.pow(n, .3))
    aggr = 8 * math.log(dfe / 20 + 1) + 30
    recency = (90 / (1 + math.pow(1.5, (days - aggr) / (aggr / 10))) + 10) / 100
    partisan_effect = 1 if internal == "" else .7
    w = n_weight * v * partisan_effect * recency * g
    return w


# CREATE VOTER GRADES #
pop_val = {'pop': ['v', 'lv', 'rv', 'a', ''], 'value': [1, 1, .67, .5, .5]}
pop_val_df = pd.DataFrame(pop_val)
df = pd.read_csv("https://projects.fivethirtyeight.com/polls-page/data/generic_ballot_polls.csv", low_memory=False,
                 parse_dates=['end_date', 'created_at'])
psters = pd.read_csv("data/pollster-ratings.csv", low_memory=False)
output = pd.read_csv("data/generic-ballot.csv", low_memory=False, )

for index, row in df.iterrows():
    popv = pop_val_df[pop_val_df['pop'] == row["population"]]['value'].values[0]
    try:
        polv = psters[psters['pollster_rating_id'] == row["pollster_rating_id"]]['grade_value'].values[0]
        bias = psters[psters['pollster_rating_id'] == row["pollster_rating_id"]]['house_bias'].values[0]
    except IndexError:
        polv = .6
        bias = 0
    df.at[index, "grade"] = polv
    df.at[index, "house_bias"] = bias
    df.at[index, "pop_value"] = popv

poll_ids = df["poll_id"].unique()
fp = pd.DataFrame()
for d in poll_ids:
    answers = df[df["poll_id"] == d]
    best_grade = max(answers["pop_value"])
    pb = answers[answers["pop_value"] == best_grade]
    fp = fp.append(pb, ignore_index=True)

max_output = parser.parse(max(output["date"]))
today = dtime.datetime.now()
start_date = today if (today - max_output).days == 1 else max_output
num_days = (today - start_date).days
output = output[output["date"] < start_date.strftime("%Y-%m-%d")]

pavg = pd.DataFrame()
for z in range(num_days + 1):
    sim_date = start_date + dtime.timedelta(days=z)
    # FILTER TO NEWEST POLL #
    op = fp[fp["end_date"] < sim_date].copy()
    u_ids = op["pollster_id"].unique()
    op['days_old'] = (sim_date - op['end_date']).dt.days
    pfsp = pd.DataFrame()
    for e in u_ids:
        psp = op[op["pollster_id"] == e]
        newest = max(psp["end_date"])
        dsp = psp[psp["end_date"] == newest]
        pfsp = pfsp.append(dsp, ignore_index=True)

    for index, row in pfsp.iterrows():
        weight = assign_weight(row["sample_size"], row["days_old"],
                               row["grade"], row["pop_value"], row["partisan"], 60)
        pfsp.at[index, "weight"] = round(weight, 3)
        partisan_effect = -3 if row["partisan"] == "REP" else 3 if row["partisan"] == "DEM" else 0
        house_bias = row["house_bias"]
        bias = (house_bias + partisan_effect)
        row["rep"] = row["rep"] + (bias / 2)
        row["dem"] = row["dem"] - (bias / 2)
        pfsp.at[index, "rep_weight"] = round(weight * row["rep"], 3)
        pfsp.at[index, "dem_weight"] = round(weight * row["dem"], 3)
    avgs = pd.DataFrame({'date': [sim_date.strftime("%Y-%m-%d")],
                         'rep': [round(pfsp["rep_weight"].sum() / pfsp["weight"].sum(), 2)],
                         'dem': [round(pfsp["dem_weight"].sum() / pfsp["weight"].sum(), 2)],
                         'margin': [
                             round((pfsp["rep_weight"].sum() - pfsp["dem_weight"].sum()) / pfsp["weight"].sum(), 2)],
                         'weight': round(pfsp["weight"].sum(), 2)})
    print(sim_date, ":", avgs["margin"][0])
    output = output.append(avgs, ignore_index=True)

output.to_csv('data/generic-ballot.csv', index=False, header=True)
