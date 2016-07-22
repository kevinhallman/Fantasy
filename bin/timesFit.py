'''
from scipy.stats import norm
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import re

with open('data/200free') as timesF:
	for line in timesF:
		timesStr = re.split(',', line)
	times = []
	for time in timesStr:
		times.append(float(time))

# best fit of data
(mu, sigma) = norm.fit(times)

# the histogram of the data
n, bins, patches = plt.hist(times, 60, normed=1, alpha=0.75)

# add a 'best fit' line
y = mlab.normpdf( bins, mu, sigma)
l = plt.plot(bins, y, 'r--', linewidth=2)

#plot
plt.show()
'''

eventDist = {'100 Yard Freestyle': 8, '50 Yard Freestyle': 9, '200 Yard Freestyle': 3}
newEventDist = {'100 Yard Freestyle': 4, '500 Yard Freestyle': 8, '200 Yard Freestyle': 8}

distNum = 20
eventDiff = distNum*2
for event in eventDist:
	if event in newEventDist:
		eventDiff -= abs(eventDist[event] - newEventDist[event])
		print abs(eventDist[event] - newEventDist[event])
	else:
		eventDiff -= eventDist[event]
		print eventDist[event]

eventDiff /= (distNum*2.0)

print eventDiff