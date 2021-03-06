from peewee import PostgresqlDatabase, ForeignKeyField, CharField, IntegerField, IntegrityError, FloatField, fn, Model, DateField, BooleanField
import os, heapq, urlparse, re, json, numpy as np, time as Time
from datetime import date as Date, timedelta
from playhouse.migrate import PostgresqlMigrator, migrate
from math import log
from scipy.stats import norm, truncnorm, skewnorm, linregress
from sympy import binomial
#import matplotlib.pyplot as plt
from events import eventsDualS, eventsChamp, allEvents, eventConvert

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


def getSkewDist(gender, division, event):
	try:
		dist = Timedist.get(gender=gender, division=division, event=event, skew=True)
		frozen = skewnorm(dist.a, dist.mu, dist.sigma)
		return frozen

	except Timedist.DoesNotExist:
		times = []  # 2016 is the only season with all the times
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
		frozen = skewnorm(a, mu, sigma)

		# save off the new dist
		newDist = Timedist(gender=gender, division=division, event=event, a=a, mu=mu, sigma=sigma, skew=True)
		newDist.save()
	return frozen


'''make time look nice'''
def swimTime(time):
	parts = re.split(r"\.", str(time))
	if not len(parts)==2:
		return time
	(seconds, point) = parts[0], parts[1]
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
	if d.month > 6:
		season = d.year + 1
	else:
		season = d.year
	startDate = Date(season - 1, 10, 14)  # use Oct 14 as the start date, prolly good for 2019
	weeksIn = int((d - startDate).days / 7)
	
	# cap at 25 weeks
	if weeksIn < 26:
		return weeksIn
	return 25

'''converts week to a date'''
def week2date(week, season=None):
	if week==None:
		return Date.today()
	if not season:
		season = thisSeason()

	startDate = Date(season - 1, 10, 14)  # use Oct 14 as the start date, prolly good for 2017
	simDate = startDate + timedelta(weeks=week)

	return simDate


'''returns current season'''
def thisSeason():
	today = Date.today()
	if today.month > 6:
		return today.year + 1
	return today.year


def seasonString(dateString):
	dateParts = re.split('/', dateString)
	if len(dateParts) < 3:
		print dateString
	year = int(dateParts[2])
	month = int(dateParts[0])
	day = int(dateParts[1])
	d = Date(year, month, day)

	if d > Date(d.year, 6, 1):
		year = d.year + 1
	else:
		year = d.year
	return year, d


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
	improvement = FloatField(null=True)
	attrition = FloatField(null=True)
	topSwimmers = {}

	def getPrevious(self, yearsBack=1):
		if yearsBack == 0:
			return self
		try:
			return TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
						   TeamSeason.division==self.division, TeamSeason.season==self.season-yearsBack)
		except TeamSeason.DoesNotExist:
			try:
				if self.gender == 'Men':
					gender_str = ' (M)'
				else:
					gender_str = ' (W)'
				return TeamSeason.get(TeamSeason.team==self.team + gender_str, TeamSeason.gender==self.gender,
						   TeamSeason.division==self.division, TeamSeason.season==self.season-yearsBack)
			except TeamSeason.DoesNotExist:
				return

	def getTaperStats(self, weeks=12, yearsback=1, toptime=True, pre_season=False):
		if pre_season:
			stats = TeamStats.get(team=self, week=weeks)
			return stats.pretaper

		lastSeason = self.getPrevious(yearsBack=yearsback)
		if not lastSeason:
			return None
			
		# underestimate taper by using later weeks
		for stats in TeamStats.select().where(TeamStats.team==lastSeason.id, TeamStats.week >= weeks).limit(1).order_by(TeamStats.week):
			if toptime:
				return stats.toptaper
			else:
				return stats.mediantaper
		return None

	def findTaperStats(self, weeks=10, topTime=True, averageTime=True, pre_season=False, this_season=True):
		newDate = week2date(week=weeks, season=self.season)
		taperSwims = self.getTaperSwims()
		dropsTop, dropsAvg, drops_previous = [], [], []

		if this_season:
			for taperSwim in taperSwims:
				# now find the top untapered swims before that date
				if topTime:
					for earlySwim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==taperSwim.swimmer,
						Swim.event==taperSwim.event, Swim.date < newDate):
						if earlySwim.min:
							dropPer = 100 * (earlySwim.min - taperSwim.time) / taperSwim.time
							dropsTop.append(dropPer)
				# use average time
				if averageTime:
					for earlySwim in Swim.select(fn.avg(Swim.time)).where(Swim.swimmer==taperSwim.swimmer,
						Swim.event==taperSwim.event, Swim.date < newDate):
						if earlySwim.avg:
							dropPer = 100 * (earlySwim.avg - taperSwim.time) / taperSwim.time
							dropsAvg.append(dropPer)

		# look for difference in last season's taper with this season
		if pre_season:
			preTeam = self.getPrevious()
			if not preTeam:
				return
			top_times = preTeam.getTaperSwims(structured=True)

			# find mid-season taper adjustments by find dif in last taper times
			for swimmer in top_times:
				for event in top_times[swimmer]:
					date = week2date(10, self.season)
					old_swim = top_times[swimmer][event]
					new_swimmer = old_swim.swimmer.nextSeason()
					if not new_swimmer: continue
					for swim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==new_swimmer, Swim.event==event, Swim.date < date):
						pass
					if swim.min:
						drops_previous.append((swim.min - old_swim.time) / ((old_swim.time + swim.min) / 2.0))
						#print old_swim.event, old_swim.name, old_swim.time, swim.min, (swim.min - old_swim.time) / ((old_swim.time + swim.min) / 2.0)
		if len(drops_previous) > 1: 
			mean_drops_pre = np.mean(drops_previous)
		else:
			mean_drops_pre = None
		if len(dropsTop) > 1: 
			stdDropTop = np.std(dropsTop)
			meanDropTop = np.mean(dropsTop)
		else:
			stdDropTop, meanDropTop = None, None
		if len(dropsAvg) > 1: 
			stdDropAvg = np.std(dropsAvg)
			meanDropAvg = np.mean(dropsAvg)
		else:
			stdDropAvg, meanDropAvg = None, None

		newStats = {'week': weeks, 'date': newDate, 'team': self.id, 'toptaper': meanDropTop, 'mediantaper': meanDropAvg}

		print newStats
		try:
			stats = TeamStats.get(TeamStats.team==self.id, TeamStats.week==weeks)
			# it exists so update it
			if meanDropTop: stats.toptaper = meanDropTop
			#if stdDropTop: stats.toptaperstd = stdDropTop
			if meanDropAvg: stats.mediantaper = meanDropAvg
			#if stdDropAvg: stats.mediantaperstd = stdDropAvg
			#if mean_drops_pre: stats.pretaper = mean_drops_pre
			stats.date = newDate
			stats.save()
		except TeamStats.DoesNotExist:
			TeamStats.insert_many([newStats]).execute()

	def getWinnats(self, previous=0):
		for stats in TeamStats.select(TeamStats.winnats, TeamStats.week).where(TeamStats.winnats.is_null(False),
				TeamStats.team==self.id).order_by(TeamStats.week.desc()).limit(1).offset(previous):
			if stats.winnats:
				return stats.winnats
		if self.winnats:
			return self.winnats
		return 0

	def getWinconf(self, previous=0):
		if not self.conference:
			return 0
		for stats in TeamStats.select(TeamStats.winconf, TeamStats.week)\
				.where(TeamStats.winconf.is_null(False), TeamStats.team==self.id, TeamStats.week > 0)\
				.order_by(TeamStats.week.desc()).limit(1).offset(previous):
			if stats.winconf:
				return stats.winconf
		if self.winconf:
			return self.winconf
		return 0

	# pulls top team strength for that year
	def getStrength(self, previous=0, invite=True, update=False):
		if invite:
			for stats in TeamStats.select(TeamStats.strengthinvite, TeamStats.week).where(TeamStats.strengthinvite.is_null(False),
					TeamStats.team==self.id).order_by(TeamStats.week.desc()).limit(1).offset(previous):
				if stats.strengthinvite:
					if update:
						self.strengthinvite = stats.strengthinvite
						self.save()
					return stats.strengthinvite
		else:
			for stats in TeamStats.select(TeamStats.strengthdual, TeamStats.week).where(TeamStats.strengthdual.is_null(
					False), TeamStats.team==self.id).limit(1).order_by(TeamStats.week.desc()).offset(previous):
				if stats.strengthdual:
					if update:
						self.strengthdual = stats.strengthdual
						self.save()
					return stats.strengthdual

		# no stats yet, so save them off
		if self.season != thisSeason():
			weeksIn = 25
		else:
			weeksIn = date2week(Date.today())
		simDate = week2date(weeksIn, self.season)
		scoreDual = self.topTeamScore(dual=True, weeksIn=weeksIn)
		scoreInvite = self.topTeamScore(dual=False, weeksIn=weeksIn)
		try:
			stats = TeamStats.get(team=self.id, week=weeksIn)
			stats.strengthdual = scoreDual
			stats.strengthinvite = scoreInvite
			stats.save()
		except TeamStats.DoesNotExist:
			TeamStats.create(team=self.id, week=weeksIn, strengthinvite=scoreInvite, strengthdual=scoreDual, date=simDate, taper=False)

		if invite:
			if update:
				self.strengthinvite = scoreInvite
				self.save()
			return scoreInvite
		else:
			if update:
				self.strengthdual = scoreDual
				self.save()
			return scoreDual

	'''top expected score for the whole team'''
	def topTeamScore(self, dual=True, weeksIn=None):
		simDate = week2date(weeksIn, self.season)

		if dual:
			events = eventsDualS
		else:
			events = eventsChamp
		topMeet = self.topTimes(events=events, date=simDate)

		topMeet.topEvents(teamMax=17, indMax=3)
		if dual:
			scores = topMeet.expectedScores(swimmers=6, division=str(self.division))
		else:
			scores = topMeet.expectedScores(swimmers=16, division=str(self.division))

		if self.team in scores:
			return scores[self.team]
		return 0

	def getTopSwimmers(self, num=10):
		swimmers = []
		for swimmer in Swimmer.select().where(Swimmer.team==self.id):
			if 'Relay' in swimmer.name: continue
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		return heapq.nlargest(num, swimmers)

	def topTimes(self, date=None, events=None):
		if not date:
			query = Swim.raw("SELECT time, event, gender, name, division, season, year, team, meet, date, team_id "
						"FROM top_swim WHERE team_id=%s  ", self.id)
		else:
			query = Swim.raw("SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM "
			"(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() "
			"OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) "
			"FROM (swim "
				"INNER JOIN swimmer sw ON swim.swimmer_id=sw.id "
				"INNER JOIN teamseason ts ON sw.team_id=ts.id) "
				"WHERE ts.id=%s and swim.date<%s "
			") AS a "
			"WHERE a.rank=1",self.id, date)

		newMeet = Meet()
		for swim in query:
			swim.gender = self.gender
			swim.season = self.season
			swim.division = self.division
			if events:
				if swim.event in events:
					newMeet.addSwim(swim)
			else:
				newMeet.addSwim(swim)

		return newMeet

	def getTaperSwims(self, numTimes=3, structured=False):
		teamSwims = set()
		if structured:
			swimDict = {}
		# grab the taper from the swimmers, assumes different events
		for swimmer in Swimmer.select().where(Swimmer.team==self.id):
			for swim in swimmer.getTaperSwims(num=numTimes).values():
				teamSwims.add(swim)
				if structured:
					if swimmer.name not in swimDict:
						swimDict[swimmer.name] = {}
					swimDict[swimmer.name][swim.event] = swim
		if structured:
			return swimDict
		else:
			return teamSwims

	def getAttrition(self, update=False, verbose=False):
		# get previous year's team, drop if null
		preTeam = self.getPrevious(1)
		if verbose: print preTeam
		if not preTeam:
			if update:
				self.attrition = None
				self.save()
			return

		teamDrops = 0
		teamSwims = 0
		for swimmer in Swimmer.select(Swimmer.name, Swimmer.team, Swimmer.year).where(
			Swimmer.team==preTeam.id):
			if verbose: print swimmer.name
			if swimmer.year=='Senior' or 'Relay' in swimmer.name:
				continue
			teamSwims += 1  # total number of swimmers
			try:
				Swimmer.get(Swimmer.name==swimmer.name, Swimmer.season==self.season, Swimmer.team==self.id)
				if verbose: print 'stay', swimmer.name
			except Swimmer.DoesNotExist:
				if verbose: print 'drop', swimmer.name
				teamDrops += 1

		if teamSwims > 0:
			dropRate = -float(teamDrops) / float(teamSwims)
		else:
			dropRate = 0

		if verbose: print dropRate
		if update:
			self.attrition = dropRate
			self.save()
			print self.id, dropRate

	def getImprovement(self, update=False):
		avgImp = 0
		for teamImp in Improvement.select(fn.avg(Improvement.improvement)).where(Improvement.team==self.team,
			Improvement.gender==self.gender, Improvement.division==self.division, Improvement.toseason==self.season):
			avgImp = teamImp.avg
		if update:
			self.improvement = avgImp
			self.save()
		return avgImp

	def deltaStrength(self, years=1):
		pre = self.getPrevious(years)
		if pre:
			return self.getStrength(update=False) - pre.getStrength(update=False)

	def nextSeason(self, years=1):
		try:
			return TeamSeason.get(TeamSeason.team==self.team, TeamSeason.gender==self.gender,
								  TeamSeason.season==self.season + years)
		except TeamSeason.DoesNotExist:
			return

	def getWeekStrength(self, weeksIn, update=True, verbose=False, dual=True, invite=True):
		if not weeksIn:
			weeksIn = 25
		simDate = week2date(weeksIn, self.season)
		if simDate > Date.today():
			print 'future date'
			return

		scoreDual, scoreInv = None, None
		# check to see if it already exists in db then update
		try:
			stats = TeamStats.get(team=self.id, week=weeksIn)
			if invite and (not stats.strengthinvite or update):
				scoreInv = self.topTeamScore(dual=False, weeksIn=weeksIn)
				stats.strengthinvite = scoreInv
				stats.date = simDate
				if verbose: print self.team, scoreInv
			if dual and (not stats.strengthdual or update):
				scoreDual = self.topTeamScore(dual=True, weeksIn=weeksIn)
				stats.strengthdual = scoreDual
				stats.date = simDate
				if verbose: print self.team, scoreDual
			stats.save()
		except TeamStats.DoesNotExist:
			if invite:
				scoreInv = self.topTeamScore(dual=False, weeksIn=weeksIn)
			else:
				scoreInv = None
			if dual:
				scoreDual = self.topTeamScore(dual=True, weeksIn=weeksIn)
			else:
				scoreDual = None
			stats = TeamStats.create(team=self.id, week=weeksIn, strengthinvite=scoreInv,
								 strengthdual=scoreDual, date=simDate)
			stats.save()
			if verbose: print self.team, scoreDual, scoreInv, stats.id

		# update team total if this is the latest week
		if scoreInv:
			for stats in TeamStats.select(TeamStats.strengthinvite, TeamStats.week) \
				.where(TeamStats.strengthinvite.is_null(False), TeamStats.team==self.id) \
				.order_by(TeamStats.week.desc()).limit(1):
				if stats.week < weeksIn or (update and stats.week == weeksIn):
					self.strengthinvite = scoreInv
					self.save()
		if scoreDual:
			for stats in TeamStats.select(TeamStats.strengthinvite, TeamStats.week) \
				.where(TeamStats.strengthdual.is_null(False), TeamStats.team==self.id) \
				.order_by(TeamStats.week.desc()).limit(1):
				if stats.week < weeksIn or (update and stats.week == weeksIn):
					self.strengthdual = scoreDual
					self.save()

	def updateSeasonStats(self):
		self.getAttrition(update=True)
		self.getImprovement(update=True)
		self.getWeekStrength(weeksIn=25, update=True, dual=False)

	'''
	Estimate how rested the team is during the season and predict the rest of the season
	'''
	def estRest(self):
		import fbprophet as prophet
		import pandas as pd

		dates = []
		drops = []
		for season in range(1, 4):
			for taper_swim in self.nextSeason(-season).getTaperSwims():
				for swim in Swim.select(Swim.time, Swim.date).where(Swim.swimmer==taper_swim.swimmer,
														 Swim.event==taper_swim.event):
					ratio = swim.time/taper_swim.time
					if ratio < 1.25:
						drops.append(ratio)
						dates.append(pd.Timestamp(swim.date))

		ts = pd.DataFrame({'y': drops, 'ds': dates})

		# now predict the rest of the current season
		m = prophet.Prophet(weekly_seasonality=False)
		m.fit(ts)
		future = m.make_future_dataframe(periods=400)
		forecast = m.predict(future)

		difs = []
		for swimmer in Swimmer.select().where(Swimmer.team==self):
			events = {}
			weights = {}
			tapers = swimmer.getTaperSwims()
			for swim in Swim.select().where(Swim.swimmer==swimmer):
				est_drop = float(forecast[forecast.ds.isin([swim.date])]['yhat'])
				if est_drop < 1:
					est_drop = 1.005
				p_time = swim.time / est_drop
				if not swim.event in tapers:
					continue
				if not swim.event in events:
					events[swim.event] = []
					weights[swim.event] = []
				events[swim.event].append(p_time)
				# two sources of error, unknown rest level,
				# poisson error (sqrt mean), weight inverse of error
				rest_error = 1/np.sqrt(est_drop - 1)
				#print p_time, est_drop, rest_error
				weights[swim.event].append(rest_error)

			# year ago
			past_swimmer = swimmer.nextSeason(-1)
			if past_swimmer:
				for swim in Swim.select().where(Swim.swimmer==past_swimmer):
					print swim.date
					print forecast[['ds', 'yhat']]
					est_drop = float(forecast[forecast.ds.isin([swim.date])]['yhat'])
					if est_drop < 1:
						est_drop = 1.005
					p_time = swim.time / est_drop
					if not swim.event in tapers:
						continue
					if not swim.event in events:
						events[swim.event] = []
						weights[swim.event] = []
					events[swim.event].append(p_time)
					# two sources of error, unknown rest level,
					# poisson error (sqrt mean), weight inverse of error
					rest_error = 1/np.sqrt(est_drop - 1)
					#print p_time, est_drop, rest_error
					weights[swim.event].append(rest_error)

			print weights, events
			#print swimmer.name
			swimmer2 = swimmer.nextSeason(-1)
			if swimmer2:
				tapers2 = swimmer2.getTaperSwims()

			print swimmer.name
			for event in events:
				predict = np.average(events[event], weights=weights[event])
				if swimmer2 and event in tapers2:
					pass
					predict = (tapers2[event].time * .995 + np.mean(events[event])) / 2
				else:
					pass
				real = tapers[event].time
				dif = (predict - real) / ((predict + real) / 2) * 100
				#print event, dif
				difs.append(dif)
				print swimTime(predict), swimTime(real)

		print difs
		print np.mean(difs), np.std(difs)
				
	class Meta:
		database = db


class TeamStats(Model):
	team = ForeignKeyField(TeamSeason)
	winnats = FloatField(null=True)
	natsscore = IntegerField(null=True)
	winconf = FloatField(null=True)
	confscore = IntegerField(null=True)
	date = DateField()  # will be the date the stats were current as of
	week = IntegerField(null=True)
	toptaper = FloatField(null=True)
	mediantaper = FloatField(null=True)
	strengthdual = FloatField(null=True)
	strengthinvite = FloatField(null=True)
	taper = BooleanField(default=False)
	class Meta:
		database = db


class Swimmer(Model):
	name = CharField()
	season = IntegerField()
	gender = CharField()
	year = CharField()
	ppts = IntegerField()
	eventppts = CharField(null=True)
	team = ForeignKeyField(TeamSeason, null=True)
	taperSwims = {}

	class Meta:
		database = db

	def predictTime(self, week, event, elite=True, division='D1', params=None, verbose=False):
		if params:
			params = params[self.gender][division]#self.team.division]

		#find previous season's best
		pre_swimmer = self.nextSeason(-1)
		pre_time, time = None, None
		#start= Time.time()
		if pre_swimmer:
			for swim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==pre_swimmer, Swim.event==event):
				pre_time = swim.min
		
		#find this season's best
		date = week2date(week=week, season=self.season)
		for swim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==self, Swim.event==event, Swim.date<date):
			time = swim.min
		#print Time.time() - start
		if verbose:
			print self.name, event
			print 'previous time', pre_time
			print 'mid top time', time

		# one time doesn't exist
		if not pre_time:
			if not time: 
				return
			return time * params[str(week-1)]['one_season']['0']

		# no current time or no current taper times (<week 7)
		if not time or week<7:
			return pre_time * params['last_season']['0']
		return time * params[str(week-1)]['two_season']['0'] + pre_time * params[str(week-1)]['two_season']['1']

	def topTime(self, event, date=None):
		if not date:
			for swim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==self, Swim.event==event):
				return swim.min
		for swim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==self, Swim.event==event, Swim.date<date):
			return swim.min
		return None

	def stats(self, distNum=20, topNum=3):  # used to find if two swimmers are similar
		topSwims = self.topSwims(distNum)

		eventDist = {}
		for swim in topSwims:
			eventDist[swim.event] = eventDist.get(swim.event, 0) + 1

		avgPpt = 0
		for swim in topSwims[:topNum]:
			avgPpt += swim.getPPTs()
		avgPpt /= topNum

		#for swim in topSwims[:topNum]:
		##	print swim.event, swim.time

		return eventDist, avgPpt

	def topSwims(self, n=20, event=None, distinctEvents=False):
		times = []
		for swim in Swim.select().where(Swim.swimmer==self, Swim.relay==False):
			swim.getPPTs(zscore=False)
			if swim.event=='1000 Free': continue
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

	def eventPPts(self):
		if self.eventppts:
			swims = {}
			parts = re.split(',', self.eventppts)
			for part in parts:
				event, points = re.split(':', part)
				swims[event] = int(points)
			return swims

		swims = {}
		for swim in self.topSwims():
			if swim.event not in swims:
				swims[swim.event] = 0
			swims[swim.event] += int(swim.powerpoints)

		pptstr = ''
		for event in swims:
			pptstr += event + ':' + str(swims[event]) + ','
		self.eventppts = pptstr[:-1]  # save as hashed string and remove trailing comma
		if len(self.eventppts)<255:
			self.save()
		return swims

	def getTaperSwims(self, num=3):
		taperSwims = {}
		times = []

		for swim in Swim.raw("WITH topTimes as "
			"(SELECT name, gender, meet, event, time, division, swimmer_id, row_number() OVER "
			"(PARTITION BY event, name ORDER BY time) as rnum "
			"FROM Swim WHERE swimmer_id=%s) "
			"SELECT name, event, meet, time, gender, division, swimmer_id FROM topTimes WHERE rnum=1",
			self.id):
			if swim.event == '1000 Free' or 'Relay' in swim.event:
				continue
			swim.year = self.year

			points = swim.getPPTs(save=False)
			heapq.heappush(times, (points, swim))

		for (points, swim) in heapq.nlargest(num, times):  # take three best times
			taperSwims[swim.event] = swim

		return taperSwims

	def getPPTs(self):
		if self.ppts:
			return self.ppts
		events = {}
		for swim in Swim.select().where(Swim.swimmer==self):
			if swim.event == '1000 Free' or 'Relay' in swim.event:
				continue
			ppts = swim.getPPTs(save=True)
			if not swim.event in events:
				events[swim.event] = ppts
			elif ppts > events[swim.event]:
				events[swim.event] = ppts
		powerpoints = sum(sorted(events.values())[-3:])
		self.ppts = powerpoints
		self.save()
		return powerpoints

	def nextSeason(self, years=1):
		try:
			return Swimmer.get(Swimmer.team==self.team.nextSeason(years=years), Swimmer.gender==self.gender,
						   Swimmer.name==self.name)
		except Swimmer.DoesNotExist:
			return


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
	division = CharField()
	relay = BooleanField()
	powerpoints = IntegerField(null=True)
	place = None
	score = None
	scoreTeam = None
	scoreTime = None
	split = False
	pastTimes = []
	taperTime = None

	def getPPTs(self, zscore=True, save=False, raw=False):
		if self.powerpoints and not raw:
			return self.powerpoints

		if not self.gender or not self.division or not self.event or not self.time:
			return None
		cdf = getSkewCDF(self.gender, self.division, self.event)
		percent = 1 - cdf(self.time)
		if percent < 0.00000000001 or not percent:
			#print self.time, self.event, self.id
			self.powerpoints = 0
			if save:
				self.save()
			return self.powerpoints

		percentileScore = (1 - percent) * 500
		powerScore = 1 / percent
		if zscore:
			zscore = log(powerScore) * 50  # approximately the number of stds away from the mean
		else:
			zscore = 0

		# print self.name, self.event, self.time, percentileScore, powerScore, zscore
		#print percent, percentileScore, zscore
		self.powerpoints = percentileScore + zscore
		if self.powerpoints > 2000:  # no bullshit check, Ledecky's 1650 is about 1000
			self.powerpoints = 0
		if save:
			self.save()
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

	def getSwimmer(self):
		if self.swimmer: 
			return self.swimmer
		team = TeamSeason.get(team=self.team, season=self.season, gender=self.gender)
		return Swimmer.get(name=self.name, team=team)
	
	def getTeam(self):
		if self.swimmer:
			return self.swimmer.team
		return TeamSeason.get(team=self.team, season=self.season, gender=self.gender)

	def getScoreTeam(self):
		if self.scoreTeam:
			return self.scoreTeam
		if isinstance(self.team, basestring):
			return self.team
		if isinstance(self.team, TeamSeason):
			return self.team.team
		return ''

	def getScoreTime(self):  # can temporarily set a new time, i.e. taper time
		if self.scoreTime:
			return self.scoreTime
		return self.time

	def getScore(self):
		if self.score:
			return self.score
		return 0

	def printScore(self, br='\t', gender=True, full_event=True):
		time = swimTime(self.getScoreTime())
		if gender and self.gender:
			genderStr = br + self.gender
		else:
			genderStr = ''
		if self.relay:
			name = 'Relay'
		else:
			name = self.name
		if self.meet:
			try:
				meet = str(self.meet)
			except:
				meet = 'unicode error'
		else:
			meet = ''
		if full_event:
			if self.event in eventConvert:
				event = eventConvert[self.event]
			else:
				event = self.event
		else:
			event = self.event

		return name+br+self.getScoreTeam()+genderStr+br+event+br+time+br+meet

	def taper(self, week, params=None, division=division):
		time = self.getSwimmer().predictTime(week=week, event=self.event, params=params, division=division)
		self.taperTime = self.scoreTime = time
		self.meet = None
		self.date = None
		return time

	def getTaperTime(self):
		if self.taperTime:
			return self.taperTime
		return self.time

	# returns the original db swim information, useful if pulled from a partition
	def sync(self):
		if self.id:
			return self
		db_swim = Swim.get(Swim.name==self.name, Swim.time<self.time+.01, Swim.time > self.time-.01,
						Swim.event==self.event, Swim.date==self.date)
		return db_swim

	def json(self):
		db_swim = self.sync()
		return {'id': db_swim.id, 'name': self.name, 'event': self.event, 'time': self.time}

	def __str__(self):
		return self.printScore()

	class Meta:
		database = db
		indexes = ('name', 'meet')


class Swimstaging(Model):
	meet = CharField()
	date = DateField()
	season = IntegerField()
	name = CharField()
	year = CharField(null=True)
	team = CharField()
	gender = CharField()
	event = CharField()
	time = FloatField()
	division = CharField()
	relay = BooleanField()
	conference = CharField(null=True)
	new = BooleanField(default=True)

	class Meta:
		database = db


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


class Meet:
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
		self.heats = 2

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
				query = query.select(Swim.name, Swim.event, Swim.team, Swim.gender, fn.Min(Swim.time), Swim.date,
								Swim.swimmer).group_by(Swim.name, Swim.event, Swim.team, Swim.gender,
															Swim.date, Swim.swimmer)
			for swim in query:
				if topSwim:
					swim.time = swim.min
					swim.meet = name
				swim.year = swim.swimmer.year
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

		if not swim.event in self.eventSwims:
			self.eventSwims[swim.event] = []

		self.eventSwims[swim.event].append(swim)

	def addSwims(self, swims, newTeamName=None):
		for swim in swims:
			if newTeamName:  # optional name override
				swim.scoreTeam = newTeamName
			self.addSwim(swim)

	def removeSwimmer(self, name):
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if swim.name==name:
					self.eventSwims[event].remove(swim)

	def remove_class(self, year='Senior'):
		for event in self.eventSwims:
			self.eventSwims[event] = [swim for swim in self.eventSwims[event] if swim.year != year or 'Relay' in event]
	
	def get_class(self, year='Freshman'):
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if swim.year==year:
					yield swim
			#self.eventSwims[event] = [swim for swim in self.eventSwims[event] if swim.year == year]

	def getEvents(self, events=''):
		myEvents = set(self.eventSwims.keys())
		if events=='':
			if not self.events:
				events = allEvents
			else:
				events = self.events
		events = set(events) & set(myEvents)
		return events

	'''
	decides top events for each swimmer
	top swimmers are decided by highest scoring event right now
	'''
	def topEvents(self, teamMax=17, indMax=3, adjEvents=False, debug=False, limit=100):
		self.place()
		conference = Meet()
		indSwims = {}
		teamSwimmers = {}
		teamDivers = {}
		drops = []
		relayEvents = set()
		events = self.eventSwims.keys()
		for team in self.teams:
			teamSwimmers[team] = 0
			teamDivers[team] = 0

		for event in self.eventSwims:  # we will keep relays as is
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
			if len(self.eventSwims[event]) > limit:
				self.eventSwims[event] = self.eventSwims[event][:limit-1]  # start with top 100 times

		# now make sure that each person swims their top events
		preEvent = None
		nextEvent = None
		if debug: print self
		while not self.isEmpty():
			for event in events:
				if 'Relay' in event:  # shouldn't
					continue
				drop = True  # just allow us to enter the loop
				while drop and not self.eventSwims[event] == []:  # we need to loop on an event until we find
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

					if not newSwim.name + newSwim.getScoreTeam() in indSwims:   # team max events
						if teamSwimmers[newSwim.getScoreTeam()] < teamMax:
							indSwims[newSwim.name + newSwim.getScoreTeam()] = 0  # count same person on two teams
							# differently
							teamSwimmers[newSwim.getScoreTeam()] += 1
						else:
							if debug: print 'team', swim.name, swim.event
							if debug: print 'team', newSwim.name, newSwim.event
							drops.append(newSwim)
							continue  # fixed to still add swim when all 18

					if indSwims[newSwim.name + newSwim.getScoreTeam()] < indMax:  # individual max events
						conference.addSwim(newSwim)
						if debug: print 'adding', newSwim
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
	creates the best lineup for the given team against another set lineup
	no two person swapping instabilities
	->must implement relay creation and switching
	'''
	def lineup(self, team, debug=False, splits=False, ppts=False):
		team = str(team)

		drops = self.topEvents(30, 3)
		self.place()

		'''
		now we have a starting point
		'''
		extras = {}  # double dictionary, swim:event
		for swim in drops:  # + dropSplits
			if swim.name not in extras:
				extras[swim.name] = {}
			extras[swim.name][swim.event] = swim

		if debug: print self

		toCheck = self.getSwims(team, False, splits=splits)
		while len(toCheck) > 0:  # double loop on all swims, trying to see if more points are scored if swapped
			swim1 = toCheck.pop()
			swims = self.getSwims(team, False, splits=splits)
			while len(swims) > 0:
				swim2 = swims.pop()

				if swim1==swim2 or swim1.event==swim2.event:
					continue

				# already in that event
				already_entered = False
				for swim in self.eventSwims[swim2.event]:
					if swim.swimmer== swim1.swimmer:
						already_entered = True
						break
				for swim in self.eventSwims[swim1.event]:
					if swim.swimmer== swim2.swimmer:
						already_entered = True
						break
				if already_entered:
					continue

				# make sure swims exist
				if swim2.name in extras and swim1.name in extras and swim2.event in extras[swim1.name] and \
						swim1.event in extras[swim2.name]:
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
							for swim in self.eventSwims[newSwim1.event]: print swim
							print newSwim2.name, newSwim2.event
							for swim in self.eventSwims[newSwim2.event]: print swim
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

		if swim2.event in self.eventSwims and swim2 in self.eventSwims[swim2.event]:  # ind swim
			self.eventSwims[swim2.event].remove(swim2)
			self.addSwim(newSwim1)
		else:  # gotta be a relay
			self.relaySwap(swim2, newSwim1)
		if swim1.event in self.eventSwims and swim1 in self.eventSwims[swim1.event]:  # ind swim
			self.eventSwims[swim1.event].remove(swim1)
			self.addSwim(newSwim2)
		else:  # gotta be a relay
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

	def taper(self, week=10, division='D1', gender='Women', verbose=False):
		start = Time.time()
		if self.isEmpty(): return

		if verbose: print 'taper performance'
		with open('bin/model_params.json') as f:
			taper_params = json.load(f)
			params = taper_params[gender][division]

		# insert all the swimmers and events we will need to taper
		db.execute_sql('CREATE TEMP TABLE swimmer_event(id INT, event VARCHAR)')
		if verbose: print Time.time() - start
		query_string = ''
		query_string += 'INSERT INTO swimmer_event VALUES '
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				query_string += "({0}, '{1}'),".format(swim._data['swimmer'], event)
		# chop trailing comma
		query_string = query_string[:-1]
		if verbose: print Time.time() - start
		db.execute_sql(query_string)
		if verbose: print Time.time() - start
		
		# find top times from this season
		date = week2date(week, 2019)
		times = {}
		for swim in Swim.raw('SELECT ranked_swims.id, ranked_swims.event, ranked_swims.time FROM ( '
			'SELECT swim.time, swimmer_event.*, rank() OVER ( '
				'PARTITION BY swimmer_event.id, swim.event '
				'ORDER BY swim.time '
			') '
			'FROM swimmer_event '
			'INNER JOIN swim ON swim.swimmer_id=swimmer_event.id and swim.event=swimmer_event.event '
			'WHERE swim.date < %s'
			') ranked_swims WHERE rank=1', date):
			if swim.id not in times:
				times[swim.id] = {}
			times[swim.id][swim.event] = {'current': swim.time}
		if verbose: print 'this season', Time.time() - start
		
		# get top times from last season
		for swim in Swim.raw('SELECT ranked_swims.id, ranked_swims.event, ranked_swims.time, ranked_swims.date FROM ( '
			'SELECT swim.time, swim.date, swimmer_event.*, rank() OVER ( '
				'PARTITION BY swimmer_event.id, swim.event '
				'ORDER BY swim.time '
			') '
			'FROM swimmer_event '
			'INNER JOIN swimmer s ON s.id=swimmer_event.id '
			'INNER JOIN teamseason ts ON s.team_id=ts.id '
			'INNER JOIN teamseason ts2 ON ts.team=ts2.team and ts.season-1=ts2.season '
			'INNER JOIN swimmer s2 ON s.name=s2.name and s2.team_id=ts2.id '
			'INNER JOIN swim ON swim.swimmer_id=s2.id and swim.event=swimmer_event.event '
			') ranked_swims WHERE rank=1'):
			times[swim.id][swim.event]['pre_time'] = swim.time
		
		db.execute_sql('DROP TABLE swimmer_event')
		if verbose: print 'last season', Time.time() - start

		# now taper based off of parameters
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				swim.meet = None
				swim.date = None
				try:
					pre_time = times[swim._data['swimmer']][swim.event]['pre_time']
				except:
					pre_time = None
				try:
					time = times[swim._data['swimmer']][swim.event]['current']
				except:
					time = None
				if verbose:
					print self.name, event
					print 'previous time', pre_time
					print 'mid top time', time

				# one time doesn't exist
				if not pre_time:
					if not time: 
						taper_time = None
					else:
						taper_time = time * params[str(week-1)]['one_season']['0']
				else:
					# no current time or no current taper times (<week 7)
					if not time or week<7:
						taper_time = pre_time * params['last_season']['0']
					else:
						taper_time = time * params[str(week-1)]['two_season']['0'] + pre_time * params[str(week-1)]['two_season']['1']
				
				swim.taperTime = swim.scoreTime = taper_time
		if verbose: print 'tapers', Time.time() - start

	'''
	gives the expected score of the top team limup as compared to the whole division
	'''
	def expectedScores(self, division='D3', swimmers=6, verbose=False):
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
				if verbose: print swim.event, swim.time, points, int(round(scores[swim.team])), losses

		for team in scores:
			scores[team] = int(round(scores[team]))

		return scores

	def place(self, events='', storePlace=True):
		events = self.getEvents(events)
		for event in events:
			if event not in self.eventSwims or len(self.eventSwims[event]) == 0:
				continue
			self.eventSwims[event] = sorted(self.eventSwims[event], key=lambda s: s.getScoreTime(), reverse=False)
			if storePlace:
				preTime = None
				for idx, swim in enumerate(self.eventSwims[event]):
					# assign same place for ties
					if swim.getScoreTime() != preTime:
						swim.place = idx + 1
					else:
						swim.place = idx
					preTime = swim.getScoreTime()

	def score(self, dual=None, events='', heatSize=8):
		events = self.getEvents(events)
		self.place(events)
		self.assignPoints(heats=self.heats, heatSize=heatSize, dual=dual, events=events)

		return self.teamScores(events)

	'''
	assigns points to the swims
	'''
	def assignPoints(self, heats=2, heatSize=8, dual=None, events=allEvents, verbose=False):
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

		# Assign scores to the swims, use previous placing
		for event in self.eventSwims:
			if event not in events and self.eventSwims[event]:  # set score of those not being swum to zero
				for swim in self.eventSwims[event]:
					swim.score = 0
			else:
				if 'Relay' in event:  # should use real relay var
					points = pointsR
				else:
					points = pointsI

				# keep track of previous swim to score ties
				preSwim = None
				teamSwims = {}
				non_scoring_swims = 0
				for swim in self.eventSwims[event]:
					swim.score = None  # reset score
					team = swim.getScoreTeam()
					if swim.place > (len(pointsI) + non_scoring_swims):
						swim.score = 0
					elif team in teamSwims and teamSwims[team] >= max:
						swim.score = 0
						non_scoring_swims += 1  # keep track of how many swims are over scoring limit per event
					else:
						# a tie, average with previous swim's score. If pre swim did not score, then don't
						if preSwim and swim.place == preSwim.place and preSwim.score > 0:
							preScore = points[swim.place - 1 - non_scoring_swims]
							if swim.place >= len(points):
								score = preScore
							else:
								score = (preScore + points[swim.place - non_scoring_swims]) / 2.0
							if score==int(score):
								score = int(score)
							swim.score = score
							preSwim.score = score
							if verbose: print swim
							if verbose: print 'tie', swim.place, swim.score, preScore, non_scoring_swims

						else:
							swim.score = points[swim.place - 1 - non_scoring_swims]
							if verbose: print swim
							if verbose: print 'tie', swim.place, swim.score, non_scoring_swims
						if team not in teamSwims:
							teamSwims[team] = 0
						teamSwims[team] += 1
					preSwim = swim

	def scoreMonteCarlo(self, dual=None, events='', heatSize=8, heats=2, sigma=.02, runs=500):
		events = self.getEvents(events)

		for event in self.eventSwims:  # assign scores to the swims
			if not event in events and self.eventSwims[event]:  # set score of those not being swum to zero
				for swim in self.eventSwims[event]:
					swim.score = 0
		
		sigmai = teamSigma = sigma * .71 # sqrt(2)/2

		teamScoresDist = []
		for _ in range(runs):  # run runs # of times
			teamTapers = {}  # team noise
			for team in self.teams:
				teamTapers[team] = np.random.normal(0, teamSigma)
			for event in self.eventSwims:  # individual swim noise
				if event not in events: continue
				for swim in self.eventSwims[event]:
					if swim.time:
						noise = np.random.normal(0, sigmai) * swim.getTaperTime()
						teamNoise = teamTapers[swim.team] * swim.getTaperTime()
						swim.scoreTime = swim.getTaperTime() + noise + teamNoise

			# place again
			self.place(events)

			# now score
			self.assignPoints(dual=dual, heats=heats, heatSize=heatSize, events=events)
			teamScoresDist.append(self.teamScores(events))

		self.reset(times=True)  # reset the times to normal

		places = {}  # stores the number of times each team was 1st, 2nd, ect.
		for score in teamScoresDist:
			for idx, (team, score) in enumerate(score):
				if not team in places:
					places[team] = []
				places[team].append(idx)
		# print places

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

		# now sort
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

	def setHeats(self, heats=2):
		self.heats = heats

	def winningTeam(self):
		if not self.scores: self.teamScores()
		if len(self.scores)<1 or len(self.scores[0])<1: return None
		return self.scores[0][0]

	# update stored win probabilities
	def update(self, division, gender, season, nats=False, taper=False, verbose=False, week=None):
		if week!= None:
			weeksIn = week
			date = week2date(weeksIn, season)
		else:
			if self.date:
				date = self.date
			else:
				date = Date.today()
			weeksIn = date2week(date)
		# score monte carlo to find win probs then reset to real scores
		self.score()
		scores = {}
		for piece in self.teamScores():
			team, score = piece[0], piece[1]
			scores[team] = score

		with open('bin/model_params.json') as f:
			taper_params = json.load(f)
		sigma = taper_params[gender][division]['last_season']['error']
		self.scoreMonteCarlo(runs=500, sigma=sigma)
		teamProb = self.getWinProb()

		if verbose:
			print 'sigma', sigma
			print 'week', weeksIn, date
			print division, gender, season
			print teamProb
			print scores

		for team in teamProb:
			try:
				teamSeason = TeamSeason.get(team=team, division=division, gender=gender, season=season)
				try:
					stats = TeamStats.get(team=teamSeason.id, week=weeksIn, taper=taper)
					score = scores[team]
					if nats:
						stats.winnats = teamProb[team]
						stats.natsscore = score
						stats.date = date
					else:
						stats.winconf = teamProb[team]
						stats.confscore = score
						stats.date = date
					if verbose: print 'Existing:', team, season, stats.winconf, stats.winnats, weeksIn, date, \
						teamSeason.id, stats.id, stats.confscore, stats.natsscore, taper
					stats.save()
				except TeamStats.DoesNotExist:
					score = self.getTeamScore(team)
					if verbose: print 'New:', team, season, teamProb[team], weeksIn, date, score, nats
					if nats:
						TeamStats.create(team=teamSeason.id, week=weeksIn, winnats=teamProb[team], natsscore=score, date=date, taper=taper)
					else:
						TeamStats.create(team=teamSeason.id, week=weeksIn, winconf=teamProb[team], confscore=score, date=date, taper=taper)
			except TeamSeason.DoesNotExist:
				if verbose: print 'wrong', team, division, gender, season

	'''
	lists swimmers by team and by points scored
	'''
	def scoreReport(self, repressSwim=False, repressTeam=False):
		self.score()
		scores = {}
		for team in self.teams:
			scores[team] = {'total': 0, 'year': {}, 'swimmer': {}, 'event': {}}
		for event in self.eventSwims:
			for swim in self.eventSwims[event]:
				if not swim.score:
					swim.score = 0
				if swim.relay:
					name = 'Relays'
				else:
					name = swim.name
				if repressSwim and (swim.score == 0 or not swim.score):
					continue   # repress zero scores

				team = swim.getScoreTeam()
				if not name in scores[team]['swimmer']:
					scores[team]['swimmer'][name] = 0
				if not event in scores[team]['event']:
					scores[team]['event'][event] = 0
				scores[team]['swimmer'][name] += swim.score
				scores[team]['total'] += swim.score
				scores[team]['event'][event] += swim.score

				year = swim.year
				if year:
					if not year in scores[team]['year']:
						scores[team]['year'][year] = 0
					scores[team]['year'][year] += swim.score

		if repressTeam:
			zeroTeams = set()
			for team in scores:
				if scores[team]['total'] == 0:
					zeroTeams.add(team)
			for team in zeroTeams:
				del(scores[team])

		return scores

	def scoreString(self, showNum='all', showScores=True, showPlace=False):
		self.score()
		string = {}
		events = self.getEvents('')
		for event in events:
			if event not in self.eventSwims: continue
			string[eventConvert[event]] = []

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
					string[eventConvert[event]].append(swimAry)
				else:
					string[eventConvert[event]].append(swimAry)
		string["scores"] = self.teamScores()
		return string

	def json(self):
		json_out = {'teams': {}}
		for swim in self.getSwims():
			team = swim.getScoreTeam()
			if not swim.getScoreTeam() in json_out['teams']:
				json_out['teams'][team] = []
			json_out['teams'][team].append(swim.json())
		json_out['scores'] = self.getScores()
		return json_out

	def __str__(self):
		events = self.getEvents()
		print 'events', events, self.events
		for event in events:
			if event not in self.eventSwims: continue
			print "-------------------------------------------------------------------------------------"
			print "Event: " + event
			for swim in self.eventSwims[event]:
				if swim.place > 30: continue
				if swim.score:
					print swim.printScore().lstrip()+"\t"+str(swim.score)
				else:
					print swim.printScore().lstrip()

		return ''


class Team(Model):
	name = CharField()
	improvement = FloatField()
	attrition = FloatField()
	strengthdual = FloatField()
	strengthinvite = FloatField()
	conference = CharField()
	division = CharField()
	gender = CharField()

	def getAttrition(self, seasons=None, update=False):
		# print self.id
		if not seasons:
			seasons = [2017, 2016, 2015, 2014, 2013, 2012]
		teamDrops = 0
		teamSwims = 0
		for season in seasons:
			try:
				# make sure there was a team both years
				seasonID = TeamSeason.get(TeamSeason.team==self.name, TeamSeason.gender==self.gender,
										  TeamSeason.season==season).id
				seasonID2 = TeamSeason.get(TeamSeason.team==self.name, TeamSeason.gender==self.gender,
										 TeamSeason.season==season + 1).id
				for swimmer in Swimmer.select(Swimmer.name, Swimmer.team, Swimmer.year).where(
								Swimmer.team==seasonID):
						if swimmer.year=='Senior' or 'relay' in swimmer.name:
							continue
						#print 'stay', swimmer.name
						teamSwims += 1  # total number of swimmers
						try:
							Swimmer.get(Swimmer.name==swimmer.name, Swimmer.season==season+1,
										Swimmer.team==seasonID2)  # swam the next year
						except Swimmer.DoesNotExist:
							#print 'drop', swimmer.name
							teamDrops += 1
			except TeamSeason.DoesNotExist:
				pass

		if teamSwims > 0:
			dropRate = -float(teamDrops) / float(teamSwims)
		else:
			dropRate = 0

		if update:
			self.attrition = dropRate
			self.save()
			print self.id, dropRate
		return dropRate

	def getImprovement(self, update=False):
		for team in Improvement.select(fn.avg(Improvement.improvement)).where(Improvement.team==self.name,
				Improvement.gender==self.gender, Improvement.division==self.division):
			avgImp = team.avg
		if not avgImp:
			avgImp = 0
		if update:
			self.improvement = avgImp
			self.save()
		return avgImp

	def getStrength(self, update=False):
		try:
			team = TeamSeason.get(team=self.name, gender=self.gender, division=self.division, season=2017)
		except TeamSeason.DoesNotExist:
			try:
				team = TeamSeason.get(team=self.name, gender=self.gender, division=self.division, season=2015)
			except TeamSeason.DoesNotExist:
				return
		invite = team.getStrength(invite=True)
		dual = team.getStrength(invite=False)
		if not invite: invite = 0
		if not dual: dual = 0
		if update:
			self.strengthdual = dual
			self.strengthinvite = invite
			self.conference = team.conference
			self.save()
		return invite, dual

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


if __name__ == '__main__':
	migrator = PostgresqlMigrator(db)
	#db.drop_table(Swimstaging)
	#db.create_table(Swimstaging)
	with db.transaction():
		migrate(
			#migrator.drop_column('teamstats', 'taper'),
			#migrator.add_column('teamstats', 'taper', TeamStats.taper),
			#migrator.drop_column('teamstats', 'pretaper'),
			#migrator.drop_column('teamstats', 'toptaperstd'),
			migrator.add_column('teamstats', 'mediantaper', TeamStats.mediantaper),
			#migrator.drop_column('teamstats', 'toptaperstd'),
			#migrator.add_column('teamstats', 'natsscore', TeamStats.natsscore)
			#migrator.add_column('swimmer', 'team_id', Swimmer.team)
			#migrator.add_column('swim', 'powerpoints', Swim.powerpoints)
		)
	

	#texas = TeamSeason.get(team='Texas', season=2018, gender='Men')
	#for swim in texas.getTaperSwims():
	#	print swim.event, swim.name, 'week 10'
	#	print swim.swimmer.predictTime(week=10, event=swim.event, elite=True)
	#	print 'real', swim.swimmer.topTime(event=swim.event)
