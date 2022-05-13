import pandas as pd
import math
import time
import datetime as dtime
import ssl
from dateutil import parser

ssl._create_default_https_context = ssl._create_unverified_context
print("APPROVAL")
# STARTING VARIABLES #
start_time = time.time()
# start_date = dtime.datetime(2021, 1, 21)  # RERUN ALL SIMULATIONS


start_date = dtime.datetime.now()  # RUN TODAY SIMULATIONS


def assign_weight(n, days, g, v, internal):
    n = 200 if n == "" else n
    n_weight = 55.22 if n > 3500 else 5 / (1 / math.pow(n, .3))
    aggr = 20
    recency = (90 / (1 + math.pow(1.5, (days - aggr) / (aggr / 10))) + 10) / 100
    partisan_effect = 1 if internal == "" else .7
    w = n_weight * v * partisan_effect * recency * g
    return w


# CREATE VOTER GRADES #
pop_val = {'pop': ['v', 'lv', 'rv', 'a', ''], 'value': [1, 1, .67, .5, .5]}
pop_val_df = pd.DataFrame(pop_val)
df = pd.read_csv("https://projects.fivethirtyeight.com/polls-page/data/president_approval_polls.csv", low_memory=False,
                 parse_dates=['end_date', 'created_at'])
psters = pd.read_csv("data/pollster-ratings.csv", low_memory=False)
output = pd.read_csv("data/biden-approval.csv", low_memory=False)

for index, row in df.iterrows():
    popv = pop_val_df[pop_val_df['pop'] == row["population"]]['value'].values[0]
    try:
        polv = psters[psters['pollster_rating_id'] == row["pollster_rating_id"]]['grade_value'].values[0]
        sym = psters[psters['pollster_rating_id'] == row["pollster_rating_id"]]['grade'].values[0]
        bias = psters[psters['pollster_rating_id'] == row["pollster_rating_id"]]['house_bias'].values[0]
    except IndexError:
        polv = .6
        bias = 0
        sym = ""
    df.at[index, "grade"] = polv
    df.at[index, "grade_symbol"] = sym
    df.at[index, "house_bias"] = bias
    df.at[index, "pop_value"] = popv

poll_ids = df["poll_id"].unique()
fp = pd.DataFrame()
for d in poll_ids:
    answers = df[df["poll_id"] == d]
    best_grade = max(answers["pop_value"])
    pb = answers[answers["pop_value"] == best_grade]
    fp = fp.append(pb, ignore_index=True)
p_output = pd.concat([fp["pollster"], fp["grade"], fp["population"],
                      fp["end_date"], fp["yes"], fp["sample_size"], fp["no"], fp["pollster_rating_id"]], axis=1)
max_output = parser.parse(max(output["date"]))
today = dtime.datetime.now()
start_date = today if (today - max_output).days == 1 else max_output
num_days = (today - start_date).days
output = output[output["date"] < start_date.strftime("%Y-%m-%d")]

pavg = pd.DataFrame()
for z in range(num_days + 1):
    sim_date = start_date + dtime.timedelta(days=z)
    # FILTER TO NEWEST POLL #
    op = fp[fp["end_date"] <= sim_date].copy()
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
                               row["grade"], row["pop_value"], "")
        pfsp.at[index, "weight"] = round(weight, 3)
        bias = 0
        row["yes"] = row["yes"] + (bias / 2)
        row["no"] = row["no"] - (bias / 2)
        pfsp.at[index, "yes_weight"] = round(weight * row["yes"], 3)
        pfsp.at[index, "no_weight"] = round(weight * row["no"], 3)
    avgs = pd.DataFrame({'date': [sim_date.strftime("%Y-%m-%d")],
                         'yes': [round(pfsp["yes_weight"].sum() / pfsp["weight"].sum(), 2)],
                         'no': [round(pfsp["no_weight"].sum() / pfsp["weight"].sum(), 2)],
                         'margin': [
                             round((pfsp["yes_weight"].sum() - pfsp["no_weight"].sum()) / pfsp["weight"].sum(), 2)],
                         'weight': round(pfsp["weight"].sum(), 2)})
    print(sim_date, ":", avgs["margin"][0])
    output = output.append(avgs, ignore_index=True)

"""for index, row in p_output.iterrows():
    print(row)
    end_date = row["end_date"].strftime("%Y-%m-%d")
    margin_bias = (row["yes"] - row["no"]) - output[output['date'] == end_date]['margin'].values[0]
    p_output.at[index, "bias"] = round(margin_bias, 1)

pollsters = p_output["pollster"].unique()
p_ids = p_output["pollster_rating_id"].unique()
p_bias = pd.DataFrame()
for i in p_ids:
    p_polls = p_output[p_output["pollster_rating_id"] == i]
    p_bias = p_bias.append(
        pd.DataFrame({'pollster': [i], 'polls': [len(p_polls)], 'bias': [round(p_polls["bias"].mean(), 2)]}))"""


output.to_csv('data/biden-approval.csv', index=False, header=True)
p_output.to_csv('data/approval-polls.csv', index=False, header=True)
# p_bias.to_csv('~/Desktop/python/data/pollster-approval-bias.csv', index=False, header=True)
