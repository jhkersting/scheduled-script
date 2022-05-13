import pandas as pd
import math
import random as rand
import time
from dateutil import parser
from scipy.stats import t
import datetime

start_time = time.time()
dem_seats = 36
rep_seats = 29
sims = 10
national_third_party = 2.5
fund_weight = 40
exp_weight = 20
today = datetime.datetime.now()

df = pd.read_csv("2022-senate/data.csv", low_memory=False)
candidates = pd.read_csv("2022-senate/senate-candidates.csv", low_memory=False)
generic_ballot = pd.read_csv("data/generic-ballot.csv", low_memory=False)
biden_approval = pd.read_csv("data/biden-approval.csv", low_memory=False)

exp_scale = pd.DataFrame([
    {"rating": "Tossup", "margin": 0},
    {"rating": "Tilt R", "margin": 3},
    {"rating": "Lean R", "margin": 5.4},
    {"rating": "Likely R", "margin": 10.0},
    {"rating": "Very Likely R", "margin": 13.0},
    {"rating": "Solid R", "margin": 20},
    {"rating": "Tilt D", "margin": -3},
    {"rating": "Lean D", "margin": -5.4},
    {"rating": "Likely D", "margin": -10.0},
    {"rating": "Very Likely D", "margin": -13.0},
    {"rating": "Solid D", "margin": -20},
    {"rating": "", "margin": 0},
])

## CONVERT EXPERT RATINGS TO MARGINS ##

experts = ["cnalysis", "cook", "inside", "sabato"]
categories = ["fund", "exp", "poll", "state_sim"]

for i, d in df.iterrows():
    exp_ratings = []
    for x in experts:
        pct = exp_scale[exp_scale["rating"] == d[x]]["margin"].values[0]
        n = d["neutral_margin"]
        if d[x] == "Solid D":
            m = pct if abs(pct) > abs(n) else n
        elif d[x] == "Solid R":
            m = pct if abs(pct) > abs(n) else n
        else:
            m = pct
        exp_ratings.append(m)
    df.at[i, "exp_margin"] = (exp_ratings[0] * .7 + exp_ratings[1] * 1.1 + exp_ratings[2] * 1.1 + exp_ratings[
        3] * 1.1) / 4
    df.at[i, "variance"] = 7

sim_date = today
ballot = generic_ballot[generic_ballot["date"] == sim_date.strftime("%Y-%m-%d")]["margin"].values[0]
approval = -biden_approval[biden_approval["date"] == sim_date.strftime("%Y-%m-%d")]["margin"].values[0]
proj_gen_ballot = ballot * .8 + approval * .1

print(proj_gen_ballot)

## FUNDAMENTALS & EXPERTS ###
for i, d in df.iterrows():
    df.at[i, "fund_margin"] = (d["neutral_margin"] + proj_gen_ballot * d["elasticity"])

for i, d in candidates.iterrows():
    s = df[df["state_id"] == d["state_id"]]
    f_margin = s["fund_margin"].values[0]
    e_margin = s["exp_margin"].values[0]
    p = d["party"]
    third_vote = national_third_party * s["third_index"].values[0]
    no_cands = len(candidates[candidates["state_id"] == d["state_id"]])
    leftover = third_vote / ((no_cands + .001) - 2)
    if p == "R":
        f_pct = (50 - leftover) + (f_margin / 2)
        e_pct = (50 - leftover) + (e_margin / 2)
    elif p == "D":
        f_pct = (50 - leftover) - (f_margin / 2)
        e_pct = (50 - leftover) - (e_margin / 2)
    else:
        f_pct = leftover
        e_pct = leftover
    candidates.at[i, "fund_weight"] = fund_weight
    candidates.at[i, "exp_weight"] = fund_weight
    candidates.at[i, "fund_pct"] = round(f_pct, 2)
    candidates.at[i, "exp_pct"] = round(e_pct, 2)

for i, d in candidates.iterrows():
    candidates.at[i, "poll_weight"] = 0
    candidates.at[i, "state_sim_weight"] = 0
    candidates.at[i, "poll_pct"] = 0
    candidates.at[i, "state_sim_pct"] = 0

for i, d in candidates.iterrows():
    pct_points = 0
    weight_points = 0
    for x in categories:
        pct_points += d[x + "_pct"] * d[x + "_weight"]
        weight_points += d[x + "_weight"]
    candidates.at[i, "proj_vote"] = round(pct_points / weight_points, 2)
    candidates.at[i, "variance"] = 7
    candidates.at[i, "index"] = i
    candidates.at[i, "win"] = 0

unique_results = pd.DataFrame()

for z in range(sims):

    nat_rand = rand.random()
    rep_seats_sim = rep_seats
    identifier = ""
    for i, d in df.iterrows():
        state_rand = rand.random()
        cands = candidates[candidates["state_id"] == d["state_id"]].copy()
        cand_rand = nat_rand * .6 + state_rand * .4
        sim_variance = t.ppf(cand_rand, 10) * d["variance"]
        st_out = []
        for k, j in cands.iterrows():
            p = j["party"]
            proj = j["proj_vote"]
            if p == "R":
                sim_pct = proj + sim_variance
            elif p == "D":
                sim_pct = proj - sim_variance
            else:
                sim_pct = proj
            st_out.append([sim_pct, j["index"], p])
        st_out.sort(key=lambda r: (r[0]), reverse=True)
        winner = st_out[0][2]
        index = st_out[0][1]
        rep_seats_sim = rep_seats_sim + 1 if winner == "R" else rep_seats_sim
        unique_results.at[z, d["state_id"]] = winner
        identifier = identifier + winner
        candidates.at[index, "win"] += 1
    unique_results.at[z, "id"] = identifier
    unique_results.at[z, "seats"] = rep_seats_sim

for i, d in candidates.iterrows():
    candidates.at[i, "win"] = round(d["win"] / sims * 100, 2)

outcomes = list(unique_results["id"])
u_outcomes = list(set(outcomes))
for i, d in unique_results.iterrows():
    count = len(unique_results[unique_results["id"] == d["id"]])
    unique_results.at[i, "prob"] = count / sims * 100

unique_results = unique_results.drop_duplicates()
unique_results.to_csv("2022-senate/unique-results.csv", index=False)
candidates.to_csv("2022-senate/candidates-output.csv", index=False)
print("--- %s seconds ---" % (time.time() - start_time))
