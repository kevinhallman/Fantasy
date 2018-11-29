import csv
import matplotlib.pyplot as plt

times = []
with open('../access_log_split.csv') as log:
	reader = csv.DictReader(log)
	for line in reader:
		#if not 'coderview' in line[' Request']:
		time = int(line[' TimeTaken']) / 1000000.0
		times.append(time)

#print times
plt.hist(times, bins=100, log=True)
plt.show()