from peewee import *
import os
import re
from datetime import date as Date
import time as Time
import urlparse
from playhouse.migrate import *
from math import log
from scipy.stats import norm, truncnorm, skewnorm
import numpy as np
import heapq
from operator import itemgetter
from sympy import binomial


allEvents = {"400 Yard Medley Relay", "400 Yard Freestyle Relay", "800 Yard Freestyle Relay",
			 "400 Yard Individual Medley", "1650 Yard Freestyle", "200 Yard Medley Relay", "200 Yard Freestyle",
			 "100 Yard Backstroke", "100 Yard Breastroke", "200 Yard Butterfly", "50 Yard Freestyle",
			 "100 Yard Freestyle", "200 Yard Backstroke", "200 Yard Breastroke", "500 Yard Freestyle",
			 "100 Yard Butterfly", "200 Yard Individual Medley", "200 Yard Freestyle Relay", '1000 Yard Freestyle',
			 '100 Yard Breastroke', '200 Yard Breastroke'}

urlparse.uses_netloc.append("postgres")
if "DATABASE_URL" in os.environ:  # production
	url = urlparse.urlparse(os.environ["DATABASE_URL"])
	db = PostgresqlDatabase(database=url.path[1:],
    	user=url.username,
    	password=url.password,
    	host=url.hostname,
    	port=url.port)
else:
	db = PostgresqlDatabase('swimdb', user='hallmank')

'''kills outliers from list greater than rsigma or less than lsigma'''
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
def getSkewCDF(gender, division, event, percent=1.0):
	def makeCDF(a, mu, sigma, percent):  # returns a frozen truncated normal CDF
		def freezeCDF(x):
			rank = skewnorm.cdf(x, a, mu, sigma)
			if rank < percent:
				return (percent - rank) * (1 / percent)
			else:
				return 0
		return freezeCDF

	try:
		dist = Timedist.get(gender=gender, division=division, event=event, skew=True)
		frozen = makeCDF(dist.a, dist.mu, dist.sigma, percent)
		return frozen

	except Timedist.DoesNotExist:
		times = [] # 2016 is the only season with all the times
		for swim in Swim.select(Swim.time).where(Swim.division==division, Swim.gender==gender, Swim.event==event,
												 Swim.season==2016):
			times.append(swim.time)
		print len(times)
		if len(times) == 0:
			return
		times = rejectOutliers(times, l=4, r=4)

		# best fit of data
		(mu, sigma) = norm.fit(times)
		(a, mu, sigma) = skewnorm.fit(times, max(times)-mu, loc=mu, scale=sigma)
		frozen = makeCDF(a, mu, sigma, percent)

		# save off the new dist
		newDist = Timedist(gender=gender, division=division, event=event, a=a, mu=mu, sigma=sigma, skew=True)
		newDist.save()
	return frozen


class TeamSeason(Model):
	season = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField(null=True)
	division = CharField()
	winnats = FloatField(null=True)
	winconf = FloatField(null=True)
	strengthdual = FloatField(null=True)
	strengthinvite = FloatField(null=True)
	topSwimmers = {}

	def getPrevious(self, yearsBack=1):
		try:
			return TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
						   TeamSeason.division==self.division, TeamSeason.season==self.season-yearsBack)
		except TeamSeason.DoesNotExist:
			return

	def getTaperStats(self, weeks=12):
		lastSeason = self.getPrevious()
		for stats in TeamStats.select().where(TeamStats.teamseasonid==lastSeason.id, TeamStats.week >= weeks)\
				.limit(1).order_by(TeamStats.week):
			return stats.toptaper, stats.toptaperstd

	def getWinnats(self, previous=0):
		for stats in TeamStats.select(TeamStats.winnats, TeamStats.week).where(TeamStats.winnats.is_null(False),
				TeamStats.teamseasonid==self.id).order_by(TeamStats.week.desc()).limit(1).offset(previous):
			if stats.winnats:
				return stats.winnats
		if self.winnats:
			return self.winnats
		return 0

	def getWinconf(self, previous=0):
		#print self.team, self.id
		if not self.conference:
			return ''
		for stats in TeamStats.select(TeamStats.winconf, TeamStats.week)\
				.where(TeamStats.winconf.is_null(False), TeamStats.teamseasonid==self.id, TeamStats.week > 0)\
				.order_by(TeamStats.week.desc()).limit(1).offset(previous):
			if stats.winconf:
				return stats.winconf
		if self.winconf:
			return self.winconf
		return 0

	def getStrength(self, previous=0, invite=True):
		if invite:
			for stats in TeamStats.select(TeamStats.strengthinvite, TeamStats.week).where(TeamStats.strengthinvite.is_null(False),
					TeamStats.teamseasonid==self.id).order_by(TeamStats.week.desc()).limit(1).offset(previous):
				if stats.strengthinvite:
					return stats.strengthinvite
			if self.strengthinvite:
				return self.strengthinvite
		else:
			for stats in TeamStats.select(TeamStats.strengthdual, TeamStats.week).where(TeamStats.strengthdual.is_null(
					False),	TeamStats.teamseasonid==self.id).limit(1).order_by(TeamStats.week.desc()).offset(previous):
				if stats.strengthdual:
					return stats.strengthdual
			if self.strengthdual:
				return self.strengthdual

	def getTopSwimmers(self, num=10):
		swimmers = []
		for swimmer in Swimmer.select().where(Swimmer.teamid==self.id):
			if 'Relay' in swimmer.name: continue
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		return heapq.nlargest(num, swimmers)

	def topTimes(self, events=None, topTimes=True, meetForm=False, date=None):
		if not events:
			events = allEvents

		topMeet = Meet(events=events)
		swimmers = {}

		select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason) \
				.where(TeamSeason.gender==self.gender, TeamSeason.team==self.team, TeamSeason.division==self.division,
			   	TeamSeason.season==self.season, Swim.event << list(events))

		if topTimes:
			if date:
				qwery = select.select(Swim.name, Swim.event, fn.Min(Swim.time), Swimmer.team, Swimmer.year).group_by(
					Swim.name, Swim.event, Swimmer.team, Swimmer.year).where(Swim.date < date)
			else:
				qwery = select.select(Swim.name, Swim.event, fn.Min(Swim.time), Swimmer.team, Swimmer.year).group_by(Swim.name,
					Swim.event, Swimmer.team, Swimmer.year)
		else:  # mean time for the season
			qwery = select.select(Swim.name, Swim.event, fn.Avg(Swim.time), Swimmer.team, Swimmer.year).group_by(Swim.name,
				Swim.event, Swimmer.team, Swimmer.year)

		for swim in qwery:
			if topTimes:
				time = swim.min
			else:
				time = swim.avg
			newSwim = Swim(name=swim.name, event=swim.event, time=time, gender=swim.gender, team=self.team,
									  season=swim.season, year=swim.swimmer.year, swimmer=swim.swimmer)
			if meetForm:
				topMeet.addSwim(newSwim)
			else:
				if not swim.name in swimmers:
						swimmers[swim.name] = {}
				swimmers[swim.name][swim.event] = newSwim

		if meetForm:
			topMeet.place()
			return topMeet

		return swimmers

	def addUpRelay(self, event):
		if event not in {'400 Yard Medley Relay', '400 Yard Freestyle Relay', '800 Yard Freestyle Relay'}:
			return

		if event=='400 Yard Freestyle Relay':
			pass


	class Meta:
		database = db


class TeamStats(Model):
	teamseasonid = ForeignKeyField(TeamSeason)
	winnats = FloatField(null=True)
	winconf = FloatField(null=True)
	date = DateField()  # will be the date the stats were current as of
	week = IntegerField(null=True)
	toptaper = FloatField(null=True)
	toptaperstd = FloatField(null=True)
	mediantaper = FloatField(null=True)
	mediantaperstd = FloatField(null=True)
	strengthdual = FloatField(null=True)
	strengthinvite = FloatField(null=True)
	class Meta:
		database = db


class MeetStats(Model):
	percent = FloatField()
	place = IntegerField()
	conference = CharField()
	numWeeks = IntegerField()
	class Meta:
		database = db


class Swimmer(Model):
	name = CharField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()
	teamid = ForeignKeyField(TeamSeason, null=True)
	taperSwims = {}

	class Meta:
		database = db

	def similarSwimmers(self, numSimilar):
		# finds n most similar swimmers
		distNum = 10
		topNum = 3
		eventDist, avgPpt = self.stats(self.id, distNum, topNum)  # we will compare on event selection and ppt

		n = 0
		similar = []
		for swimmer in Swimmer.select().where(Swimmer.year==self.year, Swimmer.gender==self.gender):
			n+=1
			if n>1000:
				break

			newEventDist, newAvgPpt = self.stats(swimmer.id)

			# print swimmer.name, newEventDist, eventDist

			eventDiff = distNum * 2  # find event selection difference
			for event in eventDist:
				if event in newEventDist:
					eventDiff -= abs(eventDist[event] - newEventDist[event])
			eventDiff /= (distNum * 2.0)

			timeDiff = abs(newAvgPpt - avgPpt)
			diff = eventDiff**2 + timeDiff

			similar.append((swimmer, eventDiff, timeDiff, diff))

			# print eventDiff, timeDiff, diff
		for swimmerStats in sorted(similar, key=itemgetter(3))[:numSimilar]:
			print swimmerStats[0].name, swimmerStats

	def stats(self, distNum=20, topNum=3):  # used to find if two swimmers are similar
		topSwims = self.topSwims(distNum)

		eventDist = {}
		for swim in topSwims:
			eventDist[swim.event] = eventDist.get(swim.event, 0) + 1

		avgPpt = 0
		for swim in topSwims[:topNum]:
			avgPpt += swim.powerpoints
		avgPpt /= topNum

		for swim in topSwims[:topNum]:
			print swim.event, swim.time

		return eventDist, avgPpt

	def topSwims(self, n=20, event=None, distinctEvents=False):
		times = []
		for swim in Swim.select().where(Swim.swimmer==self, Swim.relay==False):
			swim.getPPTs()
			if swim.event=='1000 Yard Freestyle': continue
			times.append(swim)

		times.sort(key=lambda x: x.powerpoints, reverse=True)

		if distinctEvents:  # find the top n events
			topTimes = []
			events = set()
			for swim in times:
				if swim.event in events:
					continue
				events.add(swim.event)
				topTimes.append(swim)
				if len(topTimes) == n: break

		else:  # find the top n absolute times
			topTimes = times[:n]
		if event:
			topTimes = [time for time in topTimes if time.event==event]
		return topTimes

	def getTaperSwims(self, num=3):
		taperSwims = {}
		times = []

		for swim in Swim.raw("WITH topTimes as "
			"(SELECT name, gender, meet, event, time, year, division, swimmer_id, row_number() OVER "
			"(PARTITION BY event, name ORDER BY time) as rnum "
			"FROM Swim WHERE swimmer_id=%s) "
			"SELECT name, event, meet, time, gender, division, year, swimmer_id FROM topTimes WHERE rnum=1",
			self.id):
			if swim.event == '1000 Yard Freestyle' or 'Relay' in swim.event:
				continue
			points = swim.getPPTs()
			heapq.heappush(times, (points, swim))

		for (points, swim) in heapq.nlargest(num, times):  # take three best times
			taperSwims[swim.event] = swim

		return taperSwims

	def getPPTs(self):
		totalPPts = 0
		taperSwims = self.getTaperSwims()
		for event in taperSwims:
			totalPPts += taperSwims[event].getPPTs()

		return totalPPts


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
		cdf = getSkewCDF(self.gender, self.division, self.event)
		percentileScore = (1 - cdf(self.time)) * 500
		powerScore = 1 / cdf(self.time)
		zscore = log(powerScore) * 50  # approximately the number of stds away from the means

		# print self.name, self.event, self.time, percentileScore, powerScore, zscore
		self.powerpoints = percentileScore + zscore
		return round(self.powerpoints, 3)

	def expectedPoints(self, numSwimmers=6, losses=0, percent=None):
		#print self.name, self.time, self.getScoreTime()
		scoresR = None
		if numSwimmers == 24:
			scores = [32, 28, 27, 26, 25, 24, 23, 22, 20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
		elif numSwimmers == 16:
			scores = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
		elif numSwimmers == 12:
			scores = [15, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
		else:
			# enforce max scores per team in dual format
			if not 'Relay' in self.event:
				if losses > 2:
					return 0
			else:
				if losses < 1:
					return 0
			scores = [9, 4, 3, 2, 1]
			scoresR = [11, 4, 2]

		if 'Relay' in self.event:
			if scoresR:
				scores = scoresR
			else:
				scores = [x*2 for x in scores]

		scores = scores[losses:]  # people who you know you will lose to
		totalScore = 0

		if not percent:  # now we will do a combined national, conference, and full level scoring
			percents = [.01, .2, 1.0]
		else:
			percents = [percent]

		for percent in percents:
			#print self.gender, self.division, self.event
			cdf = getSkewCDF(self.gender, self.division, self.event, percent=percent)
			win = cdf(self.getScoreTime())
			lose = 1 - win
			num = numSwimmers - losses - 1  # other swimmers

			for place, score in enumerate(scores[losses:]):
				comb = binomial(num, place)
				totalScore += score * comb * (lose**place * win**(num -place))
			#print totalScore, percent

		return totalScore / len(percents)

	def getScoreTeam(self):
		if self.scoreTeam:
			return self.scoreTeam
		if self.team:
			return self.team
		return ''

	def getScoreTime(self):  # can temporarily set a new time, i.e. taper time
		if self.scoreTime:
			return self.scoreTime
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
			self.scoreTime = self.time

		return self

	def getTaperTime(self):
		if self.taperTime:
			return self.taperTime
		return self.time

	def __str__(self):
		return self.name+self.team+self.event+str(toTime(self.time))

	class Meta:
		database = db
		indexes = ('name', 'meet')


class Improvement(Model):
	swimmer = ForeignKeyField(Swimmer, null=True)
	name = CharField()
	event = CharField()
	improvement = FloatField()
	fromtime = FloatField()
	totime = FloatField()
	fromseason = IntegerField()
	toseason = IntegerField()
	team = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	fromyear = CharField()
	toyear = CharField()

	def percentImp(self):
		return (self.fromtime - self.totime) / ((self.fromtime + self.totime) / 2)

	class Meta:
		database = db


class Meet(Model):
	season = IntegerField()
	meet = CharField()
	gender = CharField()
	date = DateField()

	class Meta:
		database = db


class TeamMeet(Model):
	team = ForeignKeyField(TeamSeason)
	meet = ForeignKeyField(Meet)

	class Meta:
		database = db


class Team(Model):
	name = CharField()
	improvement = FloatField()
	attrition = FloatField()
	strengthdual = FloatField()
	strengthinvite = FloatField()
	conference = CharField()
	division = CharField()
	gender = CharField()

	class Meta:
		database = db

'''
store time distribution data
'''
class Timedist(Model):
	event = CharField()
	gender = CharField()
	division = CharField()
	mu = FloatField()
	sigma = FloatField()
	a = FloatField(null=True)
	skew = BooleanField(null=True)

	class Meta:
		database = db

def seasonString(dateString):
	dateParts = re.split('/', dateString)
	year = int(dateParts[2])
	month = int(dateParts[0])
	day = int(dateParts[1])
	date = Date(year, month, day)

	if date > Date(date.year, 6, 1):
		year = date.year + 1
	else:
		year = date.year
	return year, date

# make time look nice
def swimTime(time):
	(seconds, point) = re.split("\.", str(time))
	if int(seconds) < 60:
		time = round(time, 2)
		time = str(time)
		while len(time) < 5:
			time += '0'
		return time
	minutes = str(int(seconds) / 60)
	seconds = str(int(seconds) % 60)
	while len(seconds) < 2:
		seconds = '0' + seconds
	while len(point) < 2:
		point = point + '0'
	return  minutes + ":" + seconds + "." + point[:2]

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

def getConfs(confFile):
	with open(confFile,'r') as file:
		teams = {}
		for line in file:
			parts = re.split('\t', line.strip())
			division = parts[0]
			conf = parts[1]
			team = parts[2]
			if not team in teams:
				teams[team] = (conf, division)
	return teams

if __name__ == '__main__':
	'''
	scores = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
	totalScore = 0
	lose = 1.0
	win = 1.0 - lose
	print win
	losses = 0
	num = 16 - losses - 1# other swimmers

	for place, score in enumerate(scores[losses:]):
		comb = binomial(num, place)
		print place, score, comb, lose**(place), win**(num - place)
		totalScore += score * comb * (lose**place * win**(num - place))
	print 'total score', totalScore
	'''
	#cdf = getSkewCDF('Women', 'D3', '200 Yard Medley Relay', .2)
	#for time in range(110, 130):
	#	print time, cdf(time)
	times = TeamSeason.get(team='Carleton', season=2017).topTimes()
	for swimmer in times:
		for event in times[swimmer]:
			print swimmer, event, times[swimmer][event].time


	'''
	migrator = PostgresqlMigrator(db)
	with db.transaction():
		migrate(
			migrator.add_column('teamstats', 'toptaperstd', TeamStats.toptaperstd),
			migrator.add_column('teamstats', 'mediantaperstd', TeamStats.mediantaperstd)
			#migrator.add_column('swimmer', 'teamid_id', Swimmer.teamid)
			#migrator.add_column('swim', 'swimmer_id', Swim.swimmer)
		)
	'''
	#db.drop_tables([Timedist])
	#db.create_tables([Timedist])


