from peewee import *
import os
import re
from datetime import date as Date
import time as Time
import urlparse
from playhouse.migrate import *
from math import log
from scipy.stats import norm, truncnorm
import numpy as np
import heapq
from operator import itemgetter
from sympy import binomial

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
		for stats in TeamStats.select(TeamStats.winnats).where(TeamStats.winnats.is_null(False),
				TeamStats.teamseasonid==self.id).limit(1).offset(previous):
			if stats.winnats:
				return stats.winnats
		if self.winnats:
			return self.winnats
		return 0

	def getWinconf(self, previous=0):
		if not self.conference:
			return ''
		for stats in TeamStats.select(TeamStats.winconf).where(TeamStats.winconf.is_null(False),
				TeamStats.teamseasonid==self.id).limit(1).offset(previous):
			if stats.winconf:
				return stats.winconf
		if self.winconf:
			return self.winconf
		return 0

	def getTopSwimmers(self, num=10):
		swimmers = []
		for swimmer in Swimmer.select().where(Swimmer.teamid==self.id):
			if 'Relay' in swimmer.name: continue
			heapq.heappush(swimmers, (swimmer.getPPTs(), swimmer))

		return heapq.nlargest(num, swimmers)

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
		slowecdf = getTimeCDF(self.gender, self.division, self.event, numsigma=1)
		fastecdf = getTimeCDF(self.gender, self.division, self.event, numsigma=-1)
		#print self.name, self.event, self.time, slowecdf(self.time), fastecdf(self.time)
		percentileScore = (1 - slowecdf(self.time)) * 1000
		#powerScore = (1 - slowecdf(self.time)) * 1000
		powerScore = 10 / log(1 + fastecdf(self.time), 10) - 10 / log(2, 10)

		print self.name, self.event, percentileScore, powerScore
		self.powerpoints = percentileScore + powerScore
		return round(self.powerpoints, 3)

	def expectedPoints(self, numSwimmers=6, losses=0, numsigma=-1):
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

		cdf = getTimeCDF(self.gender, self.division, self.event, numsigma=numsigma)
		lose = 1 - cdf(self.getScoreTime())
		win = cdf(self.getScoreTime())
		num = numSwimmers - 1 - losses  # other swimmers
		totalScore = 0

		for place, score in enumerate(scores):
			comb = binomial(num, place)
			totalScore += score * comb * (lose**(num-place) * win**(place))

		return totalScore

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


class HSSwim(Model):
	name = CharField()
	event = CharField()
	time = FloatField()
	season = IntegerField()
	team = CharField()
	gender = CharField()
	year = CharField()

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
	percent = IntegerField(null=True)

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

def loadHS():
	file = 'data/HStimesMen827.txt'

	#swimmers = Swim.where(Swim.)

	with open(file) as swimFile:
		swims = []
		for line in swimFile:
			parts = line.split('|')
			print parts
			(team, name, year, event, time, gender) = (parts[0].strip(), parts[1], int(parts[2]), parts[3], parts[4],
													   parts[5].strip())
			time = toTime(time)
			newSwim = {'season': year, 'name': name, 'team': team, 'year': 'HS',
					   'gender': gender, 'event': event, 'time': time}
			swims.append(newSwim)

	print swims

	db.connect()
	with db.transaction():
		HSSwim.insert_many(swims).execute()

'''
load in new swim times
can load in to all SQL tables if params are true
'''
def load(loadMeets=False, loadTeams=False, loadSwimmers=False, loadSwims=False, loadTeamMeets=False):
	swims = []
	swimmers = []
	swimmerKeys = set()
	newTeams = []
	teamKeys = set()
	meets = []
	meetKeys = set()
	teamMeets = []
	teamMeetKeys = set()
	root = 'data'

	teams = getConfs('data/conferences.txt')
	divisions = {}
	for swimFileName in os.listdir(root):
		match = re.search('(\D+)(\d+)([mf])new', swimFileName)
		if not match:
			continue
		div, year, gender = match.groups()

		if not (int(year) == 17) and not (int(year) == 16):
			continue
		if not 'new' in swimFileName:
			continue
		with open(root + '/' + swimFileName) as swimFile:
			if div == 'DI':
				division = 'D1'
			elif div == 'DII':
				division = 'D2'
			elif div == 'DIII':
				division = 'D3'
			print division, swimFileName

			for line in swimFile:
				swimArray = re.split('\t', line)
				meet = swimArray[0].strip()
				d = swimArray[1]
				(season, swimDate) = seasonString(d)
				name = swimArray[2]
				year = swimArray[3]
				team = swimArray[4]
				gender = swimArray[5]
				event = swimArray[6]
				time = toTime(swimArray[7])

				if not team in divisions:
					divisions[team] = division

				if team in teams:
					conference = teams[team][0]
				else:
					conference = ''


				if team=='Connecticut':
					if division=='D1':
						conference = 'American Athletic Conf'
					else:
						conference = 'NESCAC'

				if 'Relay' in event: relay = True
				else: relay = False

				if relay:
					name = team + ' Relay'

				#clear old values
				teamID = None
				meetID = None
				swimmerID = None

				if loadTeams:
					key = str(season) + team + gender + conference + division
					if not key in teamKeys:  # try each team once
						teamKeys.add(key)
						try:  # don't double add for teams not loaded yet
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
						except TeamSeason.DoesNotExist:
							newTeam = {'season': season, 'conference': conference, 'team': team, 'gender':
								gender, 'division': division}
							newTeams.append(newTeam)

				if loadMeets:
					key = str(season) + meet + gender
					if not key in meetKeys:
						meetKeys.add(key)  # try each meet once
						try:  # don't double add for meets not loaded yet
							meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						except Meet.DoesNotExist:
							newMeet = {'season': season, 'gender': gender, 'meet': meet, 'date': swimDate}
							meets.append(newMeet)

				if loadSwimmers:
					key = str(season) + name + year + team + gender
					if not key in swimmerKeys:
						swimmerKeys.add(key)
						try:
							swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team).id
						except Swimmer.DoesNotExist:
							if not teamID:
								teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
							newSwimmer = {'season': season, 'name': name, 'year': year, 'team': team, 'gender':
								gender, 'teamid': teamID}
							swimmers.append(newSwimmer)

				if loadTeamMeets:
					key = str(season) + meet + gender + team
					if not key in teamMeetKeys:
						teamMeetKeys.add(key)
						if not meetID:
							meetID = Meet.get(Meet.meet==meet, Meet.season==season, Meet.gender==gender).id
						if not teamID:
							teamID = TeamSeason.get(TeamSeason.season==season, TeamSeason.team==team,
										   TeamSeason.gender==gender, TeamSeason.conference==conference).id
						try:
							teamMeetID = TeamMeet.get(TeamMeet.meet==meetID, TeamMeet.team==teamID).id
						except TeamMeet.DoesNotExist:
							newTeamMeet = {'meet': meetID, 'team': teamID}
							teamMeets.append(newTeamMeet)

				if loadSwims:
					try:
						Swim.get(Swim.name==name, Swim.time<time+.01, Swim.time > time-.01, Swim.event==event,
							Swim.date==swimDate)  # floats in SQL and python evidently different precision
					except Swim.DoesNotExist:
						if not swimmerID and not relay:
							swimmerID = Swimmer.get(Swimmer.season==season, Swimmer.name==name, Swimmer.team==team).id
						newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'year': year, 'team': team,
					   		'gender': gender, 'event': event, 'time': time, 'conference': conference, 'division':
							division, 'relay': relay, 'swimmer': swimmerID}
						swims.append(newSwim)

	db.connect()

	if loadTeams and len(newTeams) > 0:
		print 'Teams:', len(newTeams)
		TeamSeason.insert_many(newTeams).execute()

	if loadMeets and len(meets) > 0:
		print 'Meets:', len(meets)
		Meet.insert_many(meets).execute()

	if loadSwimmers and len(swimmers) > 0:
		print 'Swimmers:', len(swimmers)
		Swimmer.insert_many(swimmers).execute()

	if loadTeamMeets and len(teamMeets) > 0:
		print 'Team Meets:', len(teamMeets)
		TeamMeet.insert_many(teamMeets).execute()

	if loadSwims and len(swims) > 0:
		print 'Swims: ', len(swims)
		Swim.insert_many(swims).execute()

	'''
	for i in range(len(newSwims) / 100):
		print i
		with db.transaction():
			print newSwims[i*100:(i+1)*100]
			Swim.insert_many(newSwims[i*100:(i+1)*100]).execute()
	'''

def deleteDups():
	# cleanup for duplicate swims
	Swim.raw('DELETE FROM Swim WHERE id IN (SELECT id FROM (SELECT id, '
        'ROW_NUMBER() OVER (partition BY meet, name, event, time ORDER BY id) AS rnum '
        'FROM Swim) t '
        'WHERE t.rnum > 1) and season=2017')

def migrateImprovement():

	migrator = PostgresqlMigrator(db)
	with db.transaction():
		migrate(
			migrator.add_column('improvement', 'swimmer_id', Improvement.swimmer)
			#migrator.add_column('swimmer', 'teamid_id', Swimmer.teamid)
			#migrator.add_column('swim', 'swimmer_id', Swim.swimmer)
		)
	count = 0
	'''
	for swimmer in Swimmer.select(Swimmer.name, Swimmer.season, Swimmer.team):
		try:

			team = TeamSeason.select().where(TeamSeason.team==swimmer.team, TeamSeason.season==swimmer.season).get()
			#print team.id, swimmer.name
			Swimmer.update(teamid=team.id).where(Swimmer.name==swimmer.name,
								Swimmer.season==swimmer.season).execute()
			count += 1
			if count %100==0:
				print count
		except Swimmer.DoesNotExist:
			pass
	'''
	for swim in Swim.select(Swim.name, Swim.season, Swim.team, Swim.relay, Swim.id).where(Swim.swimmer >> None):
		try:
			#print swim.team
			if swim.relay: continue
			swimmer = Swimmer.select().where(Swimmer.team==swim.team, Swimmer.season==swim.season,
										  Swimmer.name==swim.name).get()
			#print swimmer.id, swimmer.name, swim.id
			Swim.update(swimmer=swimmer.id).where(Swim.id==swim.id).execute()
			count += 1
			if count %100==0:
				print count
		except Swimmer.DoesNotExist:
			pass

def safeLoad():
	print 'loading teams...'
	load(loadTeams=True)
	print 'loading meets and swimmers...'
	load(loadMeets=True, loadSwimmers=True)
	print 'loading teamMeets and swims...'
	load(loadTeamMeets=True, loadSwims=True)

def addRelaySwimmers():
	'''
	relaySwimmers = []
	for swim in Swim.select(Swim.team, Swim.season, Swim.conference, Swim.gender).distinct().where(Swim.relay==True):
		try:
			teamID = TeamSeason.get(TeamSeason.season==swim.season, TeamSeason.team==swim.team,
										   TeamSeason.gender==swim.gender, TeamSeason.conference==swim.conference).id
		except TeamSeason.DoesNotExist:
			print swim.team
		relayName = swim.team + ' Relay'
		newSwim = {'season': swim.season, 'name': relayName, 'year': None, 'team': swim.team, 'gender': swim.gender,
				   'teamid': teamID}
		relaySwimmers.append(newSwim)
	print 'Swimmers: ' + str(len(relaySwimmers))
	Swimmer.insert_many(relaySwimmers).execute()
	'''
	#print relaySwimmers
	swimmers = {}
	i=0
	for swim in Swim.select(Swim.team, Swim.season, Swim.conference, Swim.gender, Swim.id).where(Swim.relay==True,
																		Swim.swimmer==None):
		i+=1
		if i%1000==0:
			print i
		key = swim.team + str(swim.season) + swim.gender
		if not key in swimmers:
			try:
				swimmerID = Swimmer.get(Swimmer.team==swim.team, Swimmer.season==swim.season,
									Swimmer.gender==swim.gender).id
				swimmers[key] = swimmerID
			except Swimmer.DoesNotExist:
				print swim.team, swim.season, swim.conference
				continue
		else:
			swimmerID = swimmers[key]

		Swim.update(swimmer=swimmerID).where(Swim.id==swim.id).execute()

if __name__ == '__main__':
	#db.drop_tables([TeamStats, MeetStats])
	#db.create_tables([TeamStats, MeetStats])
	start = Time.time()
	#for swim in Swim.select().where(Swim.name=='Hallman, Kevin').order_by(Swim.time):
	#	print swim.event, swim.time, swim.getPPTs()
	#car = TeamSeason.get(TeamSeason.team=='California', TeamSeason.gender=='Women', TeamSeason.season==2017)
	#print car.getTaperStats()
	#load(loadTeams)
	safeLoad()
	#deleteDups()
	#migrateImprovement()
	#addRelaySwimmers()
	#safeLoad()
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
	stop = Time.time()
	print stop - start


