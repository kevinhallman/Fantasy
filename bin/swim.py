from math import log
from teamSeason import TeamSeason
from scipy.stats import norm, truncnorm
import numpy as np
import re

'''
kills outliers from list greater than rsigma or less than lsigma
'''
def rejectOutliers(dataX, dataY=None, l=5, r=6):
	u = np.mean(dataX)
	s = np.std(dataX)

	if dataY:
		data = zip(dataX, dataY)
		newList = [i for i in data if (u - l*s < i[0] < u + r*s)]
		newX, newY = zip(*newList)
		return list(newX), list(newY)
	else:
		newList = [i for i in dataX if (u - l*s < i < u + r*s)]
	#print swimTime(max(newList)), swimTime(min(newList))
	#print "Num rejected: " + str(len(dataX)-len(newList))
	return newList

'''
used to find the the full distribution of times in a single event and a divsion, gender
'''
def getTimeCDF(gender, division, event, numsigma=-1):
	# creates a frozen truncated normal distribution
	def makeCDF(mu, sigma, clip):  # returns a frozen truncated normal CDF
			a = -100  # arbitrarily fast times
			b = (clip - mu) / sigma
			def defaultCDF(x):
				return truncnorm.cdf(x, a, b, mu, sigma)
			return defaultCDF

	# first check db
	try:
		dist = Timedist.get(Timedist.gender==gender, Timedist.division==division, Timedist.event==event,
					 Timedist.percent==numsigma)
		clipR = dist.mu + dist.sigma * dist.percent
		#print dist.mu, dist.sigma, clipR, dist.event
		ecdf = makeCDF(dist.mu, dist.sigma, clipR)
		return ecdf

	except Timedist.DoesNotExist:
		times = []
		for swim in Swim.select(Swim.time).where(Swim.division==division, Swim.gender==gender, Swim.event==event):
			if swim.time > 15:
				times.append(swim.time)
		if len(times) == 0:
			return
		times = rejectOutliers(times, l=5, r=5)

		# best fit of data
		(mu, sigma) = norm.fit(times)

		'''top 10,1 percent'''
		clipR = mu + sigma * numsigma  # slowest time to allow
		fastTimes = [i for i in times if i< clipR]

		#ecdfold = ECDF(fastTimes)
		ecdf = makeCDF(mu, sigma, clipR)

		newDist = Timedist(gender=gender, division=division, event=event, percent=numsigma, mu=mu, sigma=sigma)
		newDist.save()

	return ecdf


# turn time into seconds, round to two digits
def toTime(time):
	if time[-1]=='r':
		time = time[:-1]
	if not time:
		return 0
	if type(time)==float:
		return time
	if time[0]=="X" or time[0]=="x":
		time=time[1:]
	if re.match(".*:.*",time) == None:
		return float(time)
	num = float(re.split(":",time)[0])*60 +float(re.split(":",time)[1])
	return int(num) + round(num%1, 2)  # round to two decimals


class Swim(Model):
	swimmer = ForeignKeyField(Swimmer, null=True)
	name = CharField()
	event = CharField()
	date = DateField()
	time = FloatField()
	season = IntegerField()
	team = CharField()
	meet = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	relay = BooleanField()
	year = CharField()
	powerpoints = None
	place = None
	score = None
	scoreTeam = None
	scoreTime = None
	split = False
	pastTimes = []
	taperTime = None

	def getPPTs(self):
		if self.powerpoints:
			return self.powerpoints

		if not self.gender or not self.division or not self.event or not self.time:
			return None
		slowecdf = getTimeCDF(self.gender, self.division, self.event, numsigma=1)
		fastecdf = getTimeCDF(self.gender, self.division, self.event, numsigma=-1)
		percentileScore = (1 - slowecdf(self.time)) * 1000
		powerScore = 10 / log(1 + fastecdf(self.time), 10) - 10 / log(2, 10)

		#print percentileScore, powerScore
		self.powerpoints = percentileScore + powerScore
		return round(self.powerpoints, 3)

	def getScoreTeam(self):
		if self.scoreTeam:
			return self.scoreTeam
		if self.team:
			return self.team
		return ''

	def getScoreTime(self):  # can temporarily set a new time, i.e. taper time
		if self.scoreTime:
			return	self.scoreTime
		return self.time

	def generateTime(self):
		pass

	def getScore(self):
		if self.score:
			return self.score
		return 0

	def printScore(self, br='\t', gender=True):
		time = swimTime(self.getScoreTime())
		if gender:
			genderStr = br + self.gender
		else:
			genderStr = ''
		if self.relay:
			name = 'Relay'
		else:
			name = self.name
		if self.meet:
			meet = str(self.meet)
		else:
			meet = ''
		return name+br+self.getScoreTeam()+genderStr+br+self.event+br+time+br+meet

	def taper(self, weeks, noise=0):
		#print self.name, self.id, self.swimmer, self.swimmer.team, self.swimmer.id
		taper, taperStd = self.getTaperStats(weeks=weeks)
		self.taperTime = self.time - self.time * taper / 100.0 + self.time * noise
		self.scoreTime = self.time - self.time * taper / 100.0 + self.time * noise

	def improve(self, database):
		if self.division:
			division=self.division
		else:
			division='D3'

		if '1000' in self.event or 'Relay' in self.event:
			self.scoreTime = self.time
			return self
		try:
			f = database.getExtrapEvent(gender=self.gender, division=division, year=self.year, event=self.event)
			newTime = self.time + f(self.time)
			# cap improvement, regression for really slow and fast times at 2%
			if newTime > 1.02 * self.time:
				self.scoreTime = self.time * 1.02
			elif newTime < .98 * self.time:
				self.scoreTime = .98 * self.time
			else:
				self.scoreTime = newTime
		except:
			print self.time, self. event
			self.scoreTime = self.time

		return self

	def getTaperTime(self):
		if self.taperTime:
			return self.taperTime
		return self.time

	def getTaperStats(self, weeks=12):
		try:
			teamid = TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
				TeamSeason.season==self.season - 1).id
			for stats in TeamStats.select().where(TeamStats.teamseasonid==teamid, TeamStats.week >= weeks).limit(1)\
				.order_by(TeamStats.week):
				if not stats.toptaper or stats.toptaper==0:
					return 3, 3
				return stats.toptaper, stats.toptaperstd
		except:
			return 3, 3
		return 3, 3

	def __str__(self):
		return self.name + self.team + self.event + str(toTime(self.time))

	class Meta:
		database = db
		indexes = ('name', 'meet')