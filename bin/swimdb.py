from peewee import *
import os
import re
from datetime import date, timedelta
import time as Time
import urlparse
from playhouse.migrate import *
from math import log
from scipy.stats import norm, truncnorm, skewnorm
import numpy as np
import heapq
from operator import itemgetter
from sympy import binomial

eventsDualS = ["200 Yard Medley Relay","1000 Yard Freestyle","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]
eventsChamp = ["400 Yard Medley Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","400 Yard Individual Medley","1650 Yard Freestyle","200 Yard Medley Relay","200 Yard Freestyle","100 Yard Backstroke","100 Yard Breastroke","200 Yard Butterfly","50 Yard Freestyle","1 mtr Diving","3 mtr Diving","100 Yard Freestyle","200 Yard Backstroke","200 Yard Breastroke","500 Yard Freestyle","100 Yard Butterfly","200 Yard Individual Medley","200 Yard Freestyle Relay"]
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

'''used to find the the full distribution of times in a single event and a divsion, gender'''
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
		print event, division, gender, len(times)
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

'''make time look nice'''
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
	return minutes + ":" + seconds + "." + point[:2]

'''converts to a time in seconds'''
def toTime(time):
	try:
		if time[0] == "X" or time[0] == "x":
			time = time[1:]
		if re.match(".*:.*",time) == None:
			return float(time)
		return float(re.split(":", time)[0]) * 60 + float(re.split(":", time)[1])
	except TypeError:
		return 0

'''converts a date to the numbered weeks'''
def date2week(d):
	if d > date.today():
		d = date.today()
	if d.month > 6:
		season = d.year + 1
	else:
		season = d.year
	startDate = date(season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017
	weeksIn = int((d - startDate).days / 7)
	return weeksIn

'''converts week to a date'''
def week2date(week, season=None):
	if not season:
		season = thisSeason()

	startDate = date(season - 1, 10, 16)  # use Oct 15 as the start date, prolly good for 2017

	if week == None:
		return date.today()

	simDate = startDate + timedelta(weeks=week)
	if simDate > date.today():  # can't simulate with future data
		simDate = date.today()

	return simDate

'''returns current season'''
def thisSeason():
	today = date.today()
	if today.month > 6:
		return today.year + 1
	return today.year

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

	# pulls top team strength for that year
	def getStrength(self, previous=0, invite=True):
		if invite:
			for stats in TeamStats.select(TeamStats.strengthinvite, TeamStats.week).where(TeamStats.strengthinvite.is_null(False),
					TeamStats.teamseasonid==self.id).order_by(TeamStats.week.desc()).limit(1).offset(previous):
				if stats.strengthinvite:
					return stats.strengthinvite
		else:
			for stats in TeamStats.select(TeamStats.strengthdual, TeamStats.week).where(TeamStats.strengthdual.is_null(
					False), TeamStats.teamseasonid==self.id).limit(1).order_by(TeamStats.week.desc()).offset(previous):
				if stats.strengthdual:
					return stats.strengthdual

		# no stats yet, so save them off
		if self.season != thisSeason():
			weeksIn = 20
		else:
			weeksIn = date2week(date.today())
		simDate = week2date(weeksIn)
		scoreDual = self.topTeamScore(dual=True, weeksIn=weeksIn)
		scoreInvite = self.topTeamScore(dual=False, weeksIn=weeksIn)
		try:
			stats = TeamStats.get(teamseasonid=self.id, week=weeksIn)
			stats.strengthdual = scoreDual
			stats.strengthinvite = scoreInvite
			stats.save()
		except TeamStats.DoesNotExist:
			TeamStats.create(teamseasonid=self.id, week=weeksIn, strengthinvite=scoreInvite, strengthdual=scoreDual,
								 date=simDate)

		if invite:
			return scoreInvite

	'''top expected score for the whole team'''
	def topTeamScore(self, dual=True, weeksIn=None):
		# convert the week to a date
		startDate = date(self.season - 1, 10, 15)  # use Oct 15 as the start date, prolly good for 2017
		if weeksIn == None:  # can't simulate with future data
			simDate = date.today()
		else:
			simDate = startDate + timedelta(weeks=weeksIn)
		if simDate > date.today():  # can't simulate with future data
			simDate = date.today()

		if dual:
			events = eventsDualS
		else:
			events = eventsChamp
		topMeet = self.topTimes(events=events, date=simDate, meetForm=True)

		topMeet.topEvents(teamMax=17, indMax=3)
		if dual:
			scores = topMeet.expectedScores(swimmers=6, division=self.division)
		else:
			scores = topMeet.expectedScores(swimmers=16, division=self.division)

		if self.team in scores:
			return scores[self.team]
		return 0

	def getTopSwimmers(self, num=10):
		swimmers = []
		for swimmer in Swimmer.select().where(Swimmer.teamid==self.id):
			if 'Relay' in swimmer.name: continue
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		return heapq.nlargest(num, swimmers)

	def topTimes(self, events=None, topTimes=True, meetForm=False, date=None):
		if not events:
			events = allEvents

		topMeet = TempMeet(events=events)
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
			newSwim = Swim(name=swim.name, event=swim.event, time=time, gender=self.gender, team=self.team,
							division=self.division, season=swim.season, year=swim.swimmer.year, swimmer=swim.swimmer)
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
		percent = 1 - cdf(self.time)
		percentileScore = (1 - percent) * 500
		powerScore = 1 / percent
		zscore = log(powerScore) * 50  # approximately the number of stds away from the means

		# print self.name, self.event, self.time, percentileScore, powerScore, zscore
		self.powerpoints = percentileScore + zscore
		return round(self.powerpoints, 3)

	def expectedPoints(self, numSwimmers=6, losses=0, percent=None):
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
			# print self.gender, self.division, self.event
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

class TempMeet:
	def __init__(self, name=None, events=list(allEvents), gender=None, topSwim=True, teams=None, season=None):
		self.gender = gender  # None means both
		self.teams = []  # teams added as swims are
		self.scores = None
		self.eventSwims = {}
		if type(allEvents) != list:
			events = list(events)
		self.events = events
		self.name = name  # named meets are ones that actually happened
		self.date = None
		self.season = None
		self.winMatrix = None

		if isinstance(teams, basestring):
			teams = [teams]

		if not gender:
			genders = ['Men', 'Women']
		else:
			genders = [gender]

		if self.name:
			query = Swim.select().where(Swim.meet==name, Swim.gender << genders, Swim.event << events)

			if teams:
				query = query.select().where(Swim.team << teams)
			if season:
				query = query.select().where(Swim.season==season)
			if topSwim:
				query = query.select(Swim.name, Swim.event, Swim.team, Swim.gender, fn.Min(Swim.time),
					Swim.year).group_by(Swim.name, Swim.event, Swim.team, Swim.gender, Swim.year)
			for swim in query:
				if topSwim:
					swim.time = swim.min
					swim.meet = name
				self.addSwim(swim)

	def reset(self, teams=False, times=False):
		for swim in self.getSwims():
			if teams:
				swim.scoreTeam = None
			if times:
				swim.scoreTime = None

	# sees if any swims are in the meet
	def isEmpty(self):
		for event in self.eventSwims:
			if not self.eventSwims[event]==[]:
				return False
		return True

	def isDual(self):
		return len(self.teams) == 2

	def getSwims(self, team='all', relays=True, splits=False, ind=True):
		swims=set()
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if ind and (swim.team == str(team) or team=='all') and (relays or not swim.relay):
					swims.add(swim)
				if splits and swim.relay and (team=='all' or swim.team == str(team)):
					for split in swim.swims:
						swims.add(split)
		return swims

	def addSwim(self, swim):
		if not swim.getScoreTeam() in self.teams:
			self.teams.append(swim.getScoreTeam())
		if self.name and not self.date or not self.season:  # without a name, its a dummy meet
			self.date=swim.date
			self.season=swim.season

		if not swim.event in self.eventSwims:
			self.eventSwims[swim.event] = []
		self.eventSwims[swim.event].append(swim)

	def addSwims(self, swims):
		for swim in swims:
			self.addSwim(swim)

	def removeSwimmer(self, name):
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if swim.name==name:
					self.eventSwims[event].remove(swim)

	def nextYear(self, database):
		for event in self.eventSwims:
			if 'Relay' in event:
				continue
			self.eventSwims[event] = [x.improve(database) for x in self.eventSwims[event] if x.year != 'Senior']

	def getEvents(self, events=''):
		myEvents = set(self.eventSwims.keys())
		if events=='':
			if self.events == None:
				events = allEvents
			else:
				events = self.events
		events = set(events) & set(myEvents)
		return events

	'''
	decides top events for each swimmer
	top swimmers are decided by highest scoring event right now
	'''
	def topEvents(self, teamMax=17, indMax=3, totalMax=4, adjEvents=False, debug=False):
		self.place()
		conference = TempMeet()
		indSwims = {}
		relaySwims = {}
		teamSwimmers = {}
		teamDivers = {}
		drops = []
		relayEvents = set()
		events = self.eventSwims.keys()
		for team in self.teams:
			teamSwimmers[team] = 0
			teamDivers[team] = 0

		for event in self.eventSwims:  # we will keep relays as is, but count them towards total swims
			if re.search('Relay', event):
				relayEvents.add(event)
				while not self.eventSwims[event] == []:  # move relays over to new meet
					relay = self.eventSwims[event].pop()
					conference.addSwim(relay)

		for event in relayEvents:
			events.remove(event)

		# pare down
		self.place()
		for event in self.eventSwims:
			if len(self.eventSwims[event]) > 100:
				self.eventSwims[event] = self.eventSwims[event][:99]  # start with top 100 times

		# now make sure that each person swims their top events
		preEvent = None
		nextEvent = None
		if debug: print self
		while not self.isEmpty():
			for event in events:
				drop = True  # just allow us to enter the loop
				while drop and not self.eventSwims[event] == []:  # we need to loop on an event until we find
				# someone who is actually in it
					drop = False
					# print self.eventSwims[event]

					if self.events and type(self.events) == type([]) and event in self.events:
						if not self.events.index(event) == 0:
							preEvent = self.events[self.events.index(event)-1]
						if not self.events.index(event)==len(self.events)-1:
							nextEvent = self.events[self.events.index(event)+1]

					newSwim = self.eventSwims[event].pop(0)

					if preEvent in conference.eventSwims and not adjEvents:  # check to make sure no adjacent events
						for swim in conference.eventSwims[preEvent]:
							if newSwim.name == swim.name and newSwim.getScoreTeam() == swim.getScoreTeam():
								drops.append(newSwim)
								drop = True
								if debug: print 'pre', swim.name, swim.event
								if debug: print 'pre', newSwim.name, newSwim.event
								break
					if nextEvent in conference.eventSwims and not adjEvents:
						for swim in conference.eventSwims[nextEvent]:
							if newSwim.name == swim.name and newSwim.getScoreTeam() == swim.getScoreTeam():
								drop = True
								drops.append(newSwim)
								if debug: print 'post', swim.name, swim.event
								if debug: print 'post', newSwim.name, newSwim.event
								break
					if drop:  # already swimming previous or next event
						continue

					if not newSwim.name+newSwim.getScoreTeam() in indSwims:   # team max events
						if teamSwimmers[newSwim.getScoreTeam()] < teamMax:
							indSwims[newSwim.name + newSwim.getScoreTeam()] = 0  # count same person on two teams
							# differently
							teamSwimmers[newSwim.getScoreTeam()] += 1
						else:
							if debug: print 'team', swim.name, swim.event
							if debug: print 'team', newSwim.name, newSwim.event
							drops.append(newSwim)
							continue # fixed to still add swim when all 18

					if indSwims[newSwim.name + newSwim.getScoreTeam()] < indMax:  # individual max events
						conference.addSwim(newSwim)
						indSwims[newSwim.name + newSwim.getScoreTeam()] += 1
					else:
						if debug: print 'ind', swim.name, swim.event
						if debug: print 'ind', newSwim.name, newSwim.event
						drops.append(newSwim)
						drop = True  # can't swim any more events

		self.score()


		if debug:
			print teamSwimmers, indSwims, teamMax, indMax
			for swim in drops:
				print swim.name, swim.event, swim.getScoreTeam(), swim.time
		self.eventSwims = conference.eventSwims
		return drops

	'''
	adds top relays using same method in database
	'''
	def addTopRelays(self, number, team, database):
		relays = [event for event in self.events if re.search('Relay',event)]
		return database.topRelays(relays, team, self)

	'''
	creates the best lineup for the given team against another set lineup
	no two person swapping instabilities
	->must implement relay creation and switching
	'''
	def lineup(self, team, debug=False, splits=False, ppts=False):
		team=str(team)

		drops = self.topEvents(30, 3, 4)
		self.place()

		'''
		now we have a starting point
		'''
		extras = {}  # double dictionary,swim:event
		for swim in drops:  # + dropSplits
			if not swim.name in extras:
				extras[swim.name] = {}
			extras[swim.name][swim.event]=swim

		if debug: self.printout()

		toCheck = self.getSwims(team, False, splits=splits)
		while len(toCheck) > 0:  # double loop on all swims, trying to see if more points are scored if swapped
			swim1=toCheck.pop()
			swims=self.getSwims(team, False, splits=splits)
			while len(swims) > 0:
				swim2=swims.pop()
				if swim1==swim2 or swim1.event==swim2.event:
					continue
				# make sure swims exist
				if extras.has_key(swim2.name) and extras.has_key(swim1.name) and extras[swim1.name].has_key(swim2.event) and extras[swim2.name].has_key(swim1.event):
					self.score()
					if debug:
						print self.score()
						print team

					if not ppts:  # normal scoring
						oldScore = self.teamScores(sorted=False)[team]  # [swim1.event,swim2.event]
						(newSwim1, newSwim2) = self.swap(swim1, swim2, extras)
						self.score()
						newScore = self.teamScores(sorted=False)[team]  # [swim1.event,swim2.event]
					else:  # optimize powerpoints
						oldScore = self.expectedScores()
						(newSwim1, newSwim2) = self.swap(swim1, swim2, extras)
						self.score()
						newScore = self.expectedScores()

					if oldScore < newScore:  # swap in new swims
						if debug:
							print "swap"
							print newSwim1.name, newSwim1.event
							print newSwim2.name, newSwim2.event
						swims.add(newSwim1)
						swims.add(newSwim2)
						if swim1 in swims:
							swims.remove(swim1)
						if swim2 in swims:
							swims.remove(swim2)

						for swim in (newSwim1, newSwim2):
							if swim.split:  # re-add swims in those events
								for relay in self.eventSwims[newSwim1.fromRelay]:
									if relay.team==team:
										for split in relay.swims:
											if not split in toCheck:
												toCheck.add(split)
							else:
								for swim in self.eventSwims[newSwim1.event]:
									if not swim in toCheck and swim.team==team:
										toCheck.add(swim)

						if swim2 in toCheck:  # make sure second swim is not checked again
							toCheck.remove(swim2)
						swim1 = toCheck.pop()  # start checking next swim

					else:  # revert to old lineup
						self.swap(newSwim1, newSwim2, extras)
		self.score()

	'''
	given two old swims
	will swap two swims, returns two new swims
	'''
	def swap(self, swim1, swim2, extras):
		newSwim1 = extras[swim1.name][swim2.event]
		newSwim2 = extras[swim2.name][swim1.event]

		if self.eventSwims.has_key(swim2.event) and swim2 in self.eventSwims[swim2.event]: # ind swim
			self.eventSwims[swim2.event].remove(swim2)
			self.addSwim(newSwim1)
		else: # gotta be a relay
			self.relaySwap(swim2, newSwim1)
		if self.eventSwims.has_key(swim1.event) and swim1 in self.eventSwims[swim1.event]: # ind swim
			self.eventSwims[swim1.event].remove(swim1)
			self.addSwim(newSwim2)
		else: # gotta be a relay
			self.relaySwap(swim1, newSwim2)

		if not extras.has_key(swim1.name):
			extras[swim1.name] = {}
		extras[swim1.name][swim1.event]=swim1
		if not extras.has_key(swim2.name):
			extras[swim2.name] = {}
		extras[swim2.name][swim2.event] = swim2

		return newSwim1, newSwim2

	'''
	swaps someone into a relay
	given old (swim1) and new (swim2) split
	'''
	def relaySwap(self, swim1, swim2):
		for relay in self.eventSwims[swim1.fromRelay]:
			if swim1 in relay.swims:
				relay.changeSwimmer(swim1, swim2)
				return

	def taper(self, weeks=12):
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				swim.taper(weeks=weeks)

	def expectedScores(self, division='D3', swimmers=6, debug=False):
		self.place()
		scores = {}
		teamSwims = {}

		for event in self.eventSwims:
			teamSwims[event] = {}
			for swim in self.eventSwims[event]:
				if not swim.team in scores:
					scores[swim.team] = 0
				if not swim.team in teamSwims[event]:
					teamSwims[event][swim.team] = 0
				else:
					teamSwims[event][swim.team] += 1

				losses = teamSwims[event][swim.team]
				swim.division = division
				points = swim.expectedPoints(numSwimmers=swimmers, losses=losses)
				swim.score = points
				if points:
					scores[swim.team] += points
				if debug: print swim.event, swim.time, points, int(round(scores[swim.team])), losses

		for team in scores:
			scores[team] = int(round(scores[team]))

		return scores

	def place(self, events='', storePlace=False):
		events = self.getEvents(events)
		for event in events:
			if not event in self.eventSwims or len(self.eventSwims[event]) == 0:
				continue
			self.eventSwims[event] = sorted(self.eventSwims[event], key=lambda s:s.getScoreTime(), reverse=False)
			if storePlace:
				for idx, swim in enumerate(self.eventSwims[event]):
					swim.place = idx + 1

	def score(self, dual=None, events='', heatSize=8, heats=2):
		events = self.getEvents(events)
		self.place(events)
		self.assignPoints(heats=heats, heatSize=heatSize, dual=dual, events=events)

		return self.teamScores(events)

	'''
	assigns points to the swims
	'''
	def assignPoints(self, heats=2, heatSize=8, dual=None, events=allEvents):
		if dual is None:
			if len(self.teams)==2:
				dual=True
			else:
				dual=False

		max = 16
		if heats == 3:
			pointsI = [32, 28, 27, 26, 25, 24, 23, 22, 20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
		elif heats == 2:
			pointsI = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
		if heatSize == 6:
			pointsI = [15, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]

		pointsR = [x*2 for x in pointsI]
		if dual:
			max = 3
			pointsI = [9, 4, 3, 2, 1]
			pointsR = [11, 4, 2]

		for event in self.eventSwims:  # Assign scores to the swims
			if not event in events and self.eventSwims[event]:  # set score of those not being swum to zero
				for swim in self.eventSwims[event]:
					swim.score = 0
			else:
				place = 1
				teamSwims = {}
				for swim in self.eventSwims[event]:
					swim.score = None  # reset score
					if not 'Relay' in swim.event:  # should use real relay var
						team = swim.getScoreTeam()
						if place > len(pointsI) or (team in teamSwims) and teamSwims[team] >= max:
							swim.score = 0
						else:
							swim.score = pointsI[place-1]
							if not team in teamSwims:
								teamSwims[team] = 0
							teamSwims[team] += 1
							place += 1
					else:
						team = swim.getScoreTeam()
						if place > len(pointsR) or (team in teamSwims) and teamSwims[team] >= max:
							swim.score = 0
						else:
							swim.score = pointsR[place-1]
							if not team in teamSwims:
								teamSwims[team] = 0
							teamSwims[team] += 1
							place += 1

	def scoreMonteCarlo(self, dual=None, events='', heatSize=8, heats=2, sigma=.02, runs=500, teamSigma=.02,
						weeksOut=4):
		# default the sigma if we just know the date
		if weeksOut == -1:
			sigma = 0.045
			teamSigma = .02
		elif weeksOut <= 4:
			teamSigma = .01
			sigma = 0.025
		elif weeksOut <= 8:
			teamSigma = .015
			sigma = 0.035
		elif weeksOut <= 12:
			teamSigma = 0.015
			sigma = 0.0425
		elif weeksOut <= 16:
			teamSigma = 0.025
			sigma = 0.045
		elif weeksOut > 16:
			teamSigma = .0325
			sigma = 0.0375

		events = self.getEvents(events)
		#print teamSigma, sigma, weeksOut

		for event in self.eventSwims:  # Assign scores to the swims
			if not event in events and self.eventSwims[event]:  # set score of those not being swum to zero
				for swim in self.eventSwims[event]:
					swim.score = 0

		teamScoresDist = []
		for iternation in range(runs):  # run runs # of times

			teamTapers = {}  # team noise
			for team in self.teams:
				teamTapers[team] = np.random.normal(0, teamSigma)
			for event in self.eventSwims:  # individual swim noise
				for swim in self.eventSwims[event]:
					if swim.time:
						noise = np.random.normal(0, sigma) * swim.getTaperTime()
						teamNoise = teamTapers[swim.team] * swim.getTaperTime()
						swim.scoreTime = swim.getTaperTime() + noise + teamNoise

			#place again
			self.place(events)

			#now score
			self.assignPoints(dual=dual, heats=heats, heatSize=heatSize, events=events)

			teamScoresDist.append(self.teamScores(events))
		self.reset(times=True)  # reset the times to normal

		places = {}  # stores the number of times each team was 1st, 2nd, ect.
		for score in teamScoresDist:
			for idx, (team, score) in enumerate(score):
				if not team in places:
					places[team] = []
				places[team].append(idx)
		#print places

		probMatrix = {}
		for team in places:
			probMatrix[team] = [0 for _ in range(len(places))]
			for place in places[team]:
				probMatrix[team][place] += 1.0/len(places[team])  # add in each individual result

		winMatrix = {}
		for team in probMatrix:
			winMatrix[team] = probMatrix[team][0]

		self.winMatrix = winMatrix
		return probMatrix

	def getTeamWinProb(self, team):
		if not self.winMatrix:
			self.scoreMonteCarlo(dual=False)
		if not team in self.winMatrix:
			return None
		return self.winMatrix[team]

	def getWinProb(self):
		if not self.winMatrix:
			self.scoreMonteCarlo(dual=False)
		return self.winMatrix

	def teamScores(self, events='', sorted=True):
		events = self.getEvents(events)
		teams = {}

		for team in self.teams:  # make sure all the teams get some score
			teams[team] = 0

		for event in events:
			if not event in self.eventSwims: continue
			for swim in self.eventSwims[event]:
				team = swim.getScoreTeam()
				if not team in teams:
					teams[team] = 0
				teams[team] += swim.getScore()
		self.scores = teams

		if not sorted:
			return teams

		#now sort
		scores = []
		for team in teams:
			scores.append([team, teams[team]])
		scores.sort(key=lambda t: t[1], reverse=True)

		return scores

	def getTeamScore(self, team):
		if not self.scores:
			self.teamScores()
		if not team in self.scores:
			return None
		return self.scores[team]

	def getScores(self):
		if not self.scores:
			return self.teamScores()
		return self.scores

	def winningTeam(self):
		if not self.scores: self.teamScores()
		if len(self.scores)<1 or len(self.scores[0])<1: return None
		return self.scores[0][0]

	'''
	lists swimmers by team and by points scored
	'''
	def scoreReport(self, repressSwim=False, repressTeam=False):
		scores={}
		for team in self.teams:
			scores[team]={'total': 0, 'year': {}, 'swimmer': {}, 'event': {}}
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if swim.relay:
					name = 'Relays'
				else:
					name = swim.name
				if repressSwim and swim.score == 0:
					continue   # repess zero scores

				team = swim.getScoreTeam()
				if not name in scores[team]['swimmer']:
					scores[team]['swimmer'][name] = 0
				if not event in scores[team]['event']:
					scores[team]['event'][event]=0
				scores[team]['swimmer'][name] += swim.score
				scores[team]['total'] += swim.score
				scores[team]['event'][event] += swim.score
				if swim.year:
					if not swim.year in scores[team]['year']:
						scores[team]['year'][swim.year] = 0
					scores[team]['year'][swim.year] += swim.score

		if repressTeam:
			zeroTeams=set()
			for team in scores:
				if scores[team]['total'] == 0:
					zeroTeams.add(team)
			for team in zeroTeams:
				del(scores[team])

		return scores

	def printout(self, events=''):
		events=self.getEvents(events)
		for event in events:
			if event not in self.eventSwims: continue
			print "-------------------------------------------------------------------------------------"
			print "Event: " + event
			for swim in self.eventSwims[event]:
				if swim.score:
					print swim.printScore().lstrip()+"\t"+str(swim.score)
				else:
					print swim.printScore().lstrip()
		print self.scores

	def scoreString(self, showNum='all', showScores=True, showPlace=False):
		self.score()
		string = {}
		events = self.getEvents('')
		for event in events:
			if event not in self.eventSwims: continue
			string[event] = []

			# determine last scoring place
			if showNum != 'all':
				lastScoring = showNum
				place = 0
				for swim in self.eventSwims[event]:
					place += 1
					if swim.getScore() != 0 and place > lastScoring:
						lastScoring = place

			place = 0
			for swim in self.eventSwims[event]:
				place += 1
				if showNum != 'all':
					if place > lastScoring:
						break
				swimAry = re.split('\t', swim.printScore(gender=False).strip())
				if showPlace:
					swimAry.insert(0, place)
				if swim.score and showScores:
					swimAry.append(str(swim.score))
					string[event].append(swimAry)
				else:
					string[event].append(swimAry)
		string["scores"] = self.teamScores()
		return string

	def __str__(self):
		if self.name:
			return self.name
		self.printout()
		return ''

	def __eq__(self, s):
		if not type(s)==type(self): return False #not called on a season
		return self.name==s.name and self.date==s.date


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
	date = date(year, month, day)

	if date > date(date.year, 6, 1):
		year = date.year + 1
	else:
		year = date.year
	return year, date

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
	team = TeamSeason.get(team='Carleton', season=2017)
	print team.getStrength()

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


