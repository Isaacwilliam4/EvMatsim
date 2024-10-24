import subprocess
import pandas as pd
# import os

directory = 'contribs/ev'
subprocess.run(['mvn','exec:java'], cwd=directory)

# iter_dir = os.listdir('./contribs/ev/scenarios/tinytown/output/ITERS/')
# final_iter = len(iter_dir) - 1

scores = pd.read_csv('./contribs/ev/scenarios/tinytown/output/scorestats.csv')

print(scores.head())

