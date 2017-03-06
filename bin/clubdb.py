from peewee import *
import os
import re
from datetime import date as Date
import time as Time
import urlparse
from playhouse.migrate import *
from swimdb import toTime, swimTime
from scipy.stats import norm, skewnorm
#import matplotlib.pyplot as plt
import numpy as np
#import matplotlib.mlab as mlab
from math import log
from sympy import binomial
import heapq

allevents = ['1650 Free', '1500 Free', '1000 Free', '800 Free', '500 Free', '400 Free', '200 Free', '100 Free',
			 '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

#  setup database
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


'''used to find the the full CDF of times in a single event and a divsion, gender'''
def getSkewCDF(gender, age, event, course='LCM', percent=1.0):
	def makeCDF(a, mu, sigma, percent):  # returns a frozen truncated normal CDF
		def freezeCDF(x):
			rank = skewnorm.cdf(x, a, mu, sigma)
			if rank < percent:
				return (percent - rank) * (1 / percent)
			else:
				return 0
		return freezeCDF

	try:
		dist = Clubtimedist.get(gender=gender, age=age, event=event, course=course)
	except Clubtimedist.DoesNotExist:
		dist = saveSkewDist(gender, age, event, course)

	frozen = makeCDF(dist.a, dist.mu, dist.sigma, percent)
	return frozen


def getSkewDist(gender, age, event, course='LCM'):
	try:
		dist = Clubtimedist.get(gender=gender, age=age, event=event, course=course)
	except Clubtimedist.DoesNotExist:
		dist = saveSkewDist(gender, age, event, course)

	frozen = skewnorm(dist.a, dist.mu, dist.sigma)
	return frozen


def saveSkewDist(gender, age, event, course='LCM'):
		times = []
		for swim in Clubswim.select(Clubswim.time).join(Clubswimmer).where(Clubswimmer.gender==gender,
					Clubswim.event==event, Clubswimmer.age==age, Clubswim.course==course):
			times.append(swim.time / 100.0)
		print event, age, gender, course, len(times)

		if len(times) < 100:
			return
		times = rejectOutliers(times, l=4, r=4)

		# best fit of data
		(mu, sigma) = norm.fit(times)
		(a, mu, sigma) = skewnorm.fit(times, max(times)-mu, loc=mu, scale=sigma)
		#frozen = skewnorm(a, mu, sigma)

		# the histogram of the data
		#n, bins, patches = plt.hist(times, 60, normed=1)
		#y = skewnorm.pdf(bins, a, mu, sigma)

		#plt.plot(bins, y)
		#plt.show()

		# save off the new dist
		newDist = Clubtimedist(gender=gender, age=age, course=course, event=event, a=a, mu=mu, sigma=sigma)
		newDist.save()

		return newDist


'''time conversion utility'''
def convert(gender, age, event, time, toage=None, fromCourse='LCM', toCourse='SCY'):
	if fromCourse==toCourse and age==toage:
		return time
	if not toage:
		toage = age

	# align events
	if fromCourse=='SCY' and (fromCourse=='SCM' or fromCourse=='LCM'):
		if event=='500 Free':
			toevent = '400 Free'
		elif event=='1650 Free':
			toevent = '1500 Free'
		else:
			toevent = event
	elif (fromCourse=='SCM' or fromCourse=='LCM') and toCourse=='SCY':
		if event == '400 Free':
			toevent = '500 Free'
		elif event == '1500 Free':
			toevent = '1650 Free'
		else:
			toevent = event
	else:
		toevent = event

	fromdist = getSkewDist(gender, age, event, fromCourse)
	todist = getSkewDist(gender, toage, toevent, toCourse)

	# find percentile rank of course time was done in
	percent = fromdist.sf(time)

	# convert using inverse survival function
	newtime = todist.isf(percent)

	# print time, round(newtime, 2)
	return newtime


class Clubteam(Model):  # one per season
	season = IntegerField()
	team = CharField()
	gender = CharField()
	state = CharField()
	winnats = FloatField(null=True)
	strengthdual = FloatField(null=True)
	strengthinvite = FloatField(null=True)
	topSwimmers = {}

	class Meta:
		database = db


class Clubswimmer(Model):
	name = CharField()
	gender = CharField()
	relay = BooleanField()
	age = IntegerField()
	team = CharField()
	ppts = IntegerField(null=True)
	eventppts = CharField(null=True)
	taperSwims = {}

	class Meta:
		database = db

	def similarSwimmers(self, num=3):
		swims1 = self.eventPPts()
		print swims1

		# compare earlier ages as well
		previous = self.nextSeason(-1)
		if not previous:
			return

		preswims1 = previous.eventPPts()
		print preswims1

		totalDeltas = {}
		# same age and gender
		for s2 in Clubswimmer.select().where(Clubswimmer.gender==self.gender, Clubswimmer.age==self.age).order_by(
				fn.Random()).limit(10):
			if s2.id==self.id:  # don't use own times
				continue
			swims2 = s2.eventPPts()

			# compare both seasons only if they both exist
			previous2 = s2.nextSeason(-1)
			if previous and previous2:
				preswims2 = previous2.eventPPts()
				print swims2
				print preswims2

				totalDeltas[s2] = 0
				events = set(swims1.keys()) | set(swims2.keys())
				for event in events:
					if event in swims1 and event in swims2:
						totalDeltas[s2] += (swims1[event] - swims2[event]) ** 2
					elif event in swims1:
						totalDeltas[s2] += swims1[event] ** 2
					elif event in swims2:
						totalDeltas[s2] += swims2[event] ** 2

				events = set(preswims1.keys()) | set(preswims2.keys())
				for event in events:
					if event in swims1 and event in preswims1:
						totalDeltas[s2] += (preswims1[event] - preswims2[event]) ** 2
					elif event in preswims1:
						totalDeltas[s2] += preswims1[event] ** 2
					elif event in preswims2:
						totalDeltas[s2] += preswims2[event] ** 2

		# now find who was the most similar, probably can keep running total
		totalSwimmers = 0
		totalEvents = 0
		events = {}
		for swimmer, value in sorted(totalDeltas.iteritems(), key=lambda (k, v): (v, k)):
			totalSwimmers += 1
			if totalSwimmers > num:
				break
			futureSwimmer = swimmer.nextSeason()
			if futureSwimmer:
				tapers = futureSwimmer.getTaperSwims()
				for event in tapers:
					if event not in events:
						events[event] = []
					events[event].append(tapers[event].time)
					totalEvents += 1

		# now average out the times for the most similar swimmers
		predictedTapers = {}
		for event in events:
			time = np.mean(events[event])
			ppt = round(Clubswim(event=event, age=self.age, gender=self.gender, time=time,
								 course=self.course).getPPTs())
			std = np.std(events[event])
			percent = float(len(events[event]))/ float(totalEvents)
			predictedTapers[event] = {'time': time, 'std': std, 'ppts': ppt, 'percent': percent}
			print event, time, std, ppt, percent


		print 'swimmer1'
		tapers = self.getTaperSwims()
		for event in tapers:
			print event, tapers[event].time
		print 'next season'
		futureSelf = self.nextSeason()
		if futureSelf:
			futureTapers = futureSelf.getTaperSwims()
			for event in futureTapers:
				print event, futureTapers[event].time, futureTapers[event].getPPTs()

		return tapers, futureTapers, predictedTapers

	def stats(self, distNum=20, topNum=3):  # used to find if two swimmers are similar
		topSwims = self.topSwims(distNum)

		eventDist = {}
		for swim in topSwims:
			eventDist[swim.event] = eventDist.get(swim.event, 0) + 1

		avgPpt = 0
		for swim in topSwims[:topNum]:
			avgPpt += swim.getPPTs()
		avgPpt /= topNum

		return eventDist, avgPpt

	def topSwims(self, n=20, event=None, distinctEvents=False):
		times = []
		for swim in Clubswim.select().where(Clubswim.swimmer==self):
			swim.getPPTs(zscore=False)
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
		if len(self.eventppts) < 255:
			self.save()
		return swims

	def getTaperSwims(self, num=3):
		taperSwims = {}
		times = []

		for swim in Clubswim.raw("WITH topTimes as "
			"(SELECT name, gender, meet, event, time, age, clubswimmer_id, row_number() OVER "
			"(PARTITION BY event, name ORDER BY time) as rnum "
			"FROM Swim WHERE swimmer_id=%s) "
			"SELECT name, gender, meet, event, time, age, clubswimmer_id FROM topTimes WHERE rnum=1",
			self.id):
			if swim.event == '1000 Yard Freestyle' or 'Relay' in swim.event:
				continue
			points = swim.getPPTs(save=False)
			heapq.heappush(times, (points, swim))

		for (points, swim) in heapq.nlargest(num, times):  # take three best times
			taperSwims[swim.event] = swim

		return taperSwims

	def getPPTs(self):
		if self.ppts:
			return self.ppts

		totalPPts = 0
		taperSwims = self.getTaperSwims()
		for event in taperSwims:
			totalPPts += taperSwims[event].getPPTs()

		self.ppts = totalPPts
		self.save()

		return totalPPts

	def ageup(self, years=1):
		try:
			return Clubswimmer.get(team=self.team, gender=self.gender, name=self.name, age=self.age + years)
		except Clubswimmer.DoesNotExist:
			return


class Clubswim(Model):
	swimmer = ForeignKeyField(Clubswimmer)
	team = ForeignKeyField(Clubteam)
	course = CharField()
	event = CharField()
	date = DateField()
	time = IntegerField()  # we will make this the time in ms to make comparisons easy
	meet = CharField()
	powerpoints = IntegerField(null=True)
	place = None
	score = None
	scoreTeam = None
	scoreTime = None
	split = False
	pastTimes = []
	taperTime = None

	class Meta:
		database = db

	def getPPTs(self, zscore=True, save=False):
		if self.powerpoints:
			return self.powerpoints

		if not self.gender or not self.division or not self.event or not self.time:
			return None

		cdf = getSkewCDF(self.gender, self.age, self.course, self.event)
		percent = 1 - cdf(self.time)
		if percent==0 or not percent:
			print self.time, self.event, self.id
			self.powerpoints = 0
			if save:
				self.save()
			return self.powerpoints
		percentileScore = (1 - percent) * 500
		powerScore = 1 / percent
		if zscore:
			zscore = log(powerScore) * 50  # approximately the number of stds away from the means
		else:
			zscore = 0

		# print self.name, self.event, self.time, percentileScore, powerScore, zscore
		self.powerpoints = percentileScore + zscore
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
			cdf = getSkewCDF(self.gender, self.age, self.course, self.event, percent=percent)
			win = cdf(self.getScoreTime())
			lose = 1 - win
			num = numSwimmers - losses - 1  # other swimmers

			for place, score in enumerate(scores[losses:]):
				comb = binomial(num, place)
				totalScore += score * comb * (lose**place * win**(num -place))

		return totalScore / len(percents)

'''
store time distribution data
'''
class Clubtimedist(Model):
	event = CharField()
	gender = CharField()
	age = IntegerField()
	course = CharField()
	mu = FloatField()
	sigma = FloatField()
	a = FloatField(null=True)

	class Meta:
		database = db


def importSwims(loadSwims=False, loadSwimmers=False, loadTeams=False, loadage=18, year=2016):
	# 9/1 starting date
	root = 'data/club/' + str(year) + '/' + str(loadage)

	for fileName in os.listdir(root):
		if 'Club' not in fileName or 'SCM' not in fileName:
			continue
		print fileName
		parts = re.split('_', fileName)
		_, season, course, gender, event, _, loadage = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]

		print season, course, gender, event, loadage
		with open(root + '/' + fileName) as file:
			swims = []
			swimmers = []
			teams = []
			swimKeys = set()
			swimmerKeys = set()
			teamKeys = set()
			#time = None

			for line in file:
				swimParts = re.split('\t', line)
				if len(swimParts) < 8:
					continue
				try:
					meetState, name, age, team, gender, event, seconds, timeStr, date = swimParts[0], swimParts[1], \
					swimParts[2], swimParts[3], swimParts[4], swimParts[5], swimParts[6], swimParts[7], swimParts[8]
					age = int(age)
					year, state, meet = meetState[:4], meetState[5:7], meetState[8:]
					if timeStr[-1]=='r':
						timeStr = timeStr[:-1]
					time = int(toTime(timeStr) * 100)  # time in ms
				except:
					print line
					continue

				if not time or not gender in ['Men', 'Women'] or not (int(age)==int(loadage)) \
						or not event in allevents or not re.match("\d\d/\d\d/\d\d$", date):
					print (not time), (not gender in ['Men', 'Women']), not event in allevents, \
						not re.match("\d\d/\d\d/\d\d$", date), not (int(age)==int(loadage))
					print age, loadage
					print time, gender, age, event, date
					print line
					continue


				if loadTeams:
					key = team + gender + season + state
					if not key in teamKeys:
						teamKeys.add(key)
						try:
							Clubteam.get(team=team, gender=gender, season=season, state=state)
						except Clubteam.DoesNotExist:
							newTeam = {'team': team, 'gender': gender, 'season': season, 'state': state}
							#print newTeam
							teams.append(newTeam)

				if loadSwimmers:  # will have two per team from aging up
					key = name + team + gender + str(age)
					if not key in swimmerKeys:
						swimmerKeys.add(key)
						try:
							Clubswimmer.get(gender=gender, name=name, team=team, age=age)
						except Clubswimmer.DoesNotExist:
							newSwimmer = {'name': name, 'gender': gender, 'relay': False, 'age': age, 'team': team}
							#print newSwimmer
							swimmers.append(newSwimmer)

				if loadSwims:
					teamID = Clubteam.get(team=team, gender=gender, season=season, state=state).id
					swimmerID = Clubswimmer.get(gender=gender, name=name, team=team, age=age).id
					key = time, event, date, swimmerID, teamID
					if not key in swimKeys:
						swimKeys.add(key)
						try:
							Clubswim.get(time=time, event=event, date=date, swimmer=swimmerID, team=teamID)
						except Clubswim.DoesNotExist:
							newSwim = {'meet': meet, 'date': date,
								   'event': event, 'time': time, 'course': course, 'swimmer': swimmerID, 'team': teamID}
							swims.append(newSwim)
							#print newSwim


		#print swims, swimmers

		db.connect()
		if loadTeams and len(teams) > 0:
			print 'Teams:', len(teams)
			print Clubteam.insert_many(teams).execute()

		if loadSwimmers and len(swimmers) > 0:
			print 'Swimmers:', len(swimmers)
			print Clubswimmer.insert_many(swimmers).execute()

		if loadSwims and len(swims) > 0:
			print 'Swims:', len(swims)
			print Clubswim.insert_many(swims).execute()

def safeImport(age=17, year=2016):
	importSwims(loadTeams=True, loadage=age, year=year)
	importSwims(loadSwimmers=True, loadage=age, year=year)
	importSwims(loadSwims=True, loadage=age, year=year)

if __name__== '__main__':
	'''
	db.drop_tables([Clubswim])
	db.drop_tables([Clubswimmer])
	db.drop_tables([Clubteam])
	'''
	db.create_tables([Clubteam])
	db.create_tables([Clubswimmer])
	db.create_tables([Clubswim])
	db.create_tables([Clubtimedist])
	'''
	for event in allevents:
		for gender in ['Men', 'Women']:
			for age in range(8, 19):
				for course in ['SCY', 'LCM', 'SCM']:
					saveSkewDist(gender=gender, event=event, age=age, course=course)
	'''






