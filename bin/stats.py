from math import log
from itertools import permutations, product, combinations
from peewee import fn

from swimdb import TeamSeason, Swim, thisSeason, rejectOutliers, swimTime, Improvement
from events import allEvents
from scipy.stats import norm, truncnorm, skewnorm, linregress
from scipy.interpolate import UnivariateSpline
import numpy as np


MIAC = ['Carleton']

'''
statistical methods
'''
def eventProjection(self, event, time, gender, year, threshold=.002, division=None):
	if year not in {'Freshman', 'Sophomore', 'Junior'}: return

	# first find similar times done same year
	uBound = time + time * threshold
	lBound = time - time * threshold
	print time, division  #uBound, lBound

	similarSwims = []
	for swim in Swim.select().where(Swim.event==event, Swim.gender==gender, Swim.year==year, Swim.time>lBound,
									Swim.time<uBound, Swim.division==division):
		# check to see if thats a top time for that swimmer
		topSwims = self.topSwims(swim.swimmer, n=10)
		if swim in topSwims:
			similarSwims.append(swim)
			#print swim.event, swim.name, swim.time
			if len(similarSwims) > 200: break

	# now see how those swimmers did next season
	def project(year):
		times = []
		for swim in similarSwims:
			try:
				nextSwimmer = Swimmer.get(Swimmer.name==swim.name, Swimmer.team==swim.team, Swimmer.year==year)
				swims = self.topSwims(nextSwimmer.id, event=event, n=5)  # get best event time in top swims
				for swim in swims:
					times.append(swim.time)
			except Swimmer.DoesNotExist:
				pass
		return times


	times1 = project(nextYear(year))
	times2 = project(nextYear(nextYear(year)))
	times3 = project(nextYear(nextYear(nextYear(year))))
	print len(times1), len(times2), len(times3)
	print np.mean(times1), np.std(times1)
	print np.mean(times2), np.std(times2)
	print np.mean(times3), np.std(times3)

def eventProjection2(self, event, time, gender, year='Freshman', threshold=.005, division='D1'):
	uLimit = time + time*threshold
	lLimit = time - time*threshold
	times = []
	#print time, event, gender
	for imp in Improvement.select().where(Improvement.event==event,
			Improvement.gender==gender, Improvement.fromtime<uLimit, Improvement.fromtime>lLimit,
						Improvement.division==division, Improvement.fromyear==year):
		times.append(imp.totime-imp.fromtime)

	#print times
	if len(times) > 5:
		return np.mean(times), np.std(times), len(times)
		#n, bins, patches = plt.hist(times, 60, density=1, alpha=0.75)
		#plt.show()

# returns an improvement function
def getExtrapEvent(self, event, gender, year='Freshman', division='D1'):
	sentinelString = event+gender+year+division
	if sentinelString in self.eventImpCache:
		return self.eventImpCache[sentinelString]

	# get fastest, slowest times
	timeStart, timeEnd = None, None
	for swim in Swim.select(fn.Min(Swim.time), fn.Max(Swim.time)).where(Swim.event==event, Swim.gender==gender,
							Swim.division==division, Swim.year==year):
		timeStart, timeEnd = swim.min, swim.max
	if not timeStart or not timeEnd:
		return

	if '1650' in event or '1000' in event:
		interval = 2
	elif '100' in event or '50' in event:
		interval =.25
	elif '200' in event:
		interval =.5
	elif '400' in event or '500' in event:
		interval = 1
	else:
		interval = 1

	timeCurve, x, y, w = [], [], [], []
	for time in np.arange(timeStart, timeEnd, interval):
		data = self.eventProjection2(event, time, gender)
		if data:
			mu, sigma, n = data
			timeCurve.append((time, round(mu, 2), round(sigma,2)))
			x.append(time)
			y.append(mu)
			w.append(1/sigma)

	f = UnivariateSpline(x, y, w)

	self.eventImpCache[sentinelString] = f
	return f

#imp cacl
def fitEvent(event, gender, division=None, plot=True):
	timesX = []
	timesY = []
	dif = []
	timesXW, timesYW, difW = [], [], []
	if division:
		improvementsMen = Improvement.select().where(Improvement.event==event, Improvement.gender=='Men',
												  Improvement.division==division)
		improvementsWomen = Improvement.select().where(Improvement.event==event, Improvement.gender=='Women',
												  Improvement.division==division)
	else:
		improvementsMen = Improvement.select().where(Improvement.event==event, Improvement.gender=='Men')
		improvementsWomen = Improvement.select().where(Improvement.event==event, Improvement.gender=='Women')

	for time in improvementsMen:
		timesX.append(time.fromtime)
		timesY.append(time.totime)
		dif.append((time.fromtime - time.totime) / ((time.fromtime + time.totime) / 2) * 100)
	for time in improvementsWomen:
		timesXW.append(time.fromtime)
		timesYW.append(time.totime)
		difW.append((time.fromtime - time.totime) / ((time.fromtime + time.totime) / 2) * 100)

	if len(timesX)<10: return
	print event
	slope, intercept, r_value, p_value, std_err = linregress(timesX, timesY)
	print slope, intercept, r_value, p_value, std_err, event
	timesX, dif = rejectOutliers(timesX, dif, l=10, r=3)
	timesXW, difW = rejectOutliers(timesXW, difW, l=10, r=3)

	timeStart = min(timesX)
	timeEnd = max(timesX)
	timeStartW = min(timesXW)
	timeEndW = max(timesXW)
	print timeStart, timeEnd
	newX = np.arange(timeStart, timeEnd, .25)

	# 2nd degree fix on the time, absolute time dropped
	fit, res, _, _, _= np.polyfit(timesX, dif, 1, full=True)
	fitW, resW, _, _, _= np.polyfit(timesXW, difW, 1, full=True)
	#print res, np.mean(dif), np.std(dif)

	fit_fn = np.poly1d(fit)
	fit_fnW = np.poly1d(fitW)

	if plot:
		figure = {
			"data": [
				go.Scatter(
					x=timesX,
					y=dif,
					mode='markers',
					name='Men'
				),
				go.Scatter(
					x=timesXW,
					y=difW,
					mode='markers',
					name='Women'
				),
				go.Scatter(
					x=[timeStart, timeEnd],
					y=[fit_fn(timeStart), fit_fn(timeEnd)],
					mode='line',
					name='Men Fit'
				),
				go.Scatter(
					x=[timeStartW, timeEndW],
					y=[fit_fnW(timeStartW), fit_fnW(timeEndW)],
					mode='line',
					name='Women Fit'
				)
			],
			"layout": go.Layout(title=event)
		}
		py.iplot(figure, filename=event)

#event meet combination
def eventCombos(topNum=20000):  # find most commonly swum event combinations, returns correlation matrix
	# find rates of each combo, powerpoints for each combo and the correlation matrix
	combos = {}
	pptCombos = {}
	corrMatrix = {}
	n = 0
	for swimmer in Swimmer.select(Swimmer.id).where(Swimmer.season==2016):
		swims = self.topSwims(swimmer.id, season=2016, n=3, distinctEvents=True)  # get their top three swims in
		# different events
		if len(swims) < 3: continue
		n+=1
		if n >topNum:
			break
		events = []
		for swim in swims:
			events.append(swim.event)
		#print events
		events.sort()
		eventStr = ''
		for event in events:
			eventStr+=' - ' + event
		combos[eventStr] = combos.get(eventStr, 0) + 1

		cdf = self.getTimeCDF(swim.gender, swim.division, swim.event, 100)
		points = 1 - cdf(swim.time)
		pptCombos[eventStr] = pptCombos.get(eventStr, 0) + points

		for perm in permutations(events, 2):
			if perm[0] not in corrMatrix:
				corrMatrix[perm[0]] = {}
			corrMatrix[perm[0]][perm[1]] = corrMatrix[perm[0]].get(perm[1], 0) + 1

	comboMatrix = [['Event Combination', '% of All Combinations', 'Power Ranking']]
	totalNum = sum(combos.values())
	for combo, value in sorted(combos.items(), key=itemgetter(1)):
		comboMatrix.append([combo[3:], round(value / float(totalNum), 2), round(pptCombos[combo] / float(value),2)])
		print combo[3:], round(value / float(totalNum), 2), round(pptCombos[combo] / float(value), 2)

	'''
	eventHeader = ''
	for event in corrMatrix:
		eventHeader += event + '\t'
	print eventHeader

	for event in corrMatrix:
		eventLine = event
		for event2 in corrMatrix:  # some of these events might not be in inner matrix
			if event2 in corrMatrix[event]:
				eventLine += '\t' + str(corrMatrix[event][event2])
			else:
				eventLine += '\t' + '0'
		print eventLine
	'''
	dataMatrix = []
	for idx1, event1 in enumerate(corrMatrix):
		dataMatrix.append([])
		for idx2, event2 in enumerate(corrMatrix):
			try:
				total = sum(corrMatrix[event1].values())
				# normalize
				dataMatrix[idx1].append(float(corrMatrix[event1][event2])/total)
			except KeyError:
				dataMatrix[idx1].append(0)

	figure = {
		"data": [
			go.Heatmap(
				z=dataMatrix,
				x=corrMatrix.keys(),
				y=corrMatrix.keys()
			)
		],
		"layout": go.Layout(title="Event Correlations", margin={'l': 175, 'b': 150})
	}
	py.plot(figure, filename="teamDropFitWomen.html")

	return corrMatrix

def bestMeet(corrMatrix, topNum=10):

	# first get all possible 3-day meet formats
	events = list(eventsChampInd) #['100 Yard Freestyle', '200 Yard Freestyle', '100 Yard Butterfly']#
	possMeets = []
	# all possible ways to split events into three groups
	flaglist = product([1, 2, 3], repeat=len(events))
	for n, flags in enumerate(flaglist):  # now apply partitions to events
		l1 = [events[i] for i, flag in enumerate(flags) if flag==1]
		l2 = [events[i] for i, flag in enumerate(flags) if flag==2]
		l3 = [events[i] for i, flag in enumerate(flags) if flag==3]
		possMeets.append((l1, l2, l3))

	# add correlations for events that are on the same day
	meetScores = {}
	lineupCombos = set()
	for meet in possMeets:
		doubled = 0
		meetStrings = []
		for day in meet:
			str = ''
			for event in sorted(day):
				str += event
			if not str == '':
				meetStrings.append(str)
			for combo in combinations(day, 2):
				if combo[0] in corrMatrix and combo[1] in corrMatrix[combo[0]]:
					doubled += corrMatrix[combo[0]][combo[1]]

		meetString = ''
		for day in sorted(meetStrings):
			meetString += day + ' -  '
		if meetString not in lineupCombos:
			meetScores[meetString] = doubled
			lineupCombos.add(meetString)


	#return the top n
	n=0
	for lineup in sorted(meetScores.items(), key=operator.itemgetter(1)):
		n+=1
		if n >topNum: break
		print lineup

def impStats(division='D1', gender='Women', season=2016):
	teamStr = []
	teamNames = []
	teamImp = {}
	teamImpOrdered = []

	# top 25 teams
	for stats in Team.select().where(Team.gender==gender, Team.division==division).order_by(
			Team.strengthinvite.desc()).limit(25):
		strength = self.topTeamScore(stats.name, dual=False, division=division, gender=gender, season=season)
		teamNames.append(stats.name)
		teamStr.append(strength)
		teamImpOrdered.append(stats.improvement)

	# get all the improvement data for each team
	boxes = []
	teamImpMeans = []
	for team in teamNames:
		teamImp[team] = []
		for stats in Improvement.select().where(Improvement.team==team, Improvement.gender==gender):
			teamImp[team].append(stats.percentImp())
		boxes.append(go.Box(y=teamImp[team], name=team))
		teamImpMeans.append(np.mean(teamImp[team]))

	print np.mean(stats.improvement), division, gender

	slope, intercept, r_value, p_value, std_err = linregress(teamStr, teamImpMeans)
	print slope, intercept, r_value, p_value, std_err

	fit, res, _, _, _= np.polyfit(teamStr, teamImpMeans, 1, full=True)
	print res


	fit_fn = np.poly1d(fit)

	start = min(teamStr)
	end = max(teamStr)

	boxes.append(go.Scatter(
				x=[start, end],
				y=[fit_fn(start), fit_fn(end)],
				name="Best Fit",
			))

	#offline.plot({'data': boxes}, filename='teamDropsMen.html')
	print teamStr, teamImpOrdered
	figure = {
		"data": [
			go.Scatter(
				x=teamStr,
				y=teamImpOrdered,
				mode='markers+text',
				name="Women's Teams",
				text=teamNames,
				textposition='top'
			)#,
			#go.Scatter(
			#	x=[start, end],
			#	y=[fit_fn(start), fit_fn(end)],
			#	name="Best Fit",
			#)
		],
		"layout": go.Layout()
	}
	py.plot(figure, filename="teamDropFitWomen.html")

def getTimeMode(gender, division, event):
	import matplotlib.pyplot as plt
	#from scipy.stats import skewnorm
	times = []
	for swim in Swim.select(Swim.time).where(Swim.division==division, Swim.gender==gender, Swim.event==event,
											 Swim.season==2016):
		if swim.time > 15:
			times.append(swim.time)
	if len(times) == 0:
		return
	times = rejectOutliers(times, l=4, r=4)
	(mu, sigma) = norm.fit(times)

	topNums = (0, 0)
	topCount = 0
	#print mu, sigma
	for i in range(50):
		hi = mu - mu*(24.5-i)/250
		lo = mu - mu*(25.5-i)/250
		count = Swim.select(fn.COUNT(Swim.id)).where(Swim.division==division, Swim.gender==gender,
						Swim.event==event, Swim.time<hi, Swim.time>lo, Swim.season==2016).scalar()
		#print hi, lo, count
		if count > topCount:
			topCount = count
			topNums = (lo, hi)
	mode = (topNums[0] + topNums[1])/2
	print event, mu, sigma, max(times)
	fit = skewnorm.fit(times, max(times)-mu, loc=mu, scale=sigma)
	print fit
	# fit2 = (-mu, fit[1], fit[2], sigma
	# mun, sigman = mode, sigma
	# fit2 = (-mu, (max(times)-mun)/(sigman), mun, sigman)
	# print fit2
	r = skewnorm(*fit)
	plt.hist(r.rvs(100000), bins=50, density=1)
	plt.hist(times, bins=50, density=1, alpha=0.5)
	plt.show()

def improvement(gender='Men', teams=MIAC, events=allEvents, season1=thisSeason()-1, season2=thisSeason()-2,
				season3=None, season4=None):
	# get top times for the seasons
	top1 = self.taperSwims(teams=teams, gender=gender, season=season1)
	top2 = self.taperSwims(teams=teams, gender=gender, season=season2)
	if season3:
		top3 = self.topTimes(gender=gender, events=events, teams=teams, season=season3, meetForm=False)
	if season4:
		top4 = self.topTimes(gender=gender, events=events, teams=teams, season=season4, meetForm=False)

	# finds improvement between two seasons
	def calcImprovement(top1, top2):
		allImprovement = {}
		teamImprovement = {}
		for team in top1:
			if not team in top2:
				continue
			if not team in allImprovement:
				allImprovement[team] = {}
				teamImprovement[team] = []
			for swimmer in top1[team]:
				if not swimmer in top2[team]:
					continue
				if not swimmer in allImprovement:
					allImprovement[team][swimmer] = {}
				for event in top1[team][swimmer]:
					if not event in top2[team][swimmer]:
						continue
					time1 = top1[team][swimmer][event].time
					time2 = top2[team][swimmer][event].time
					drop = (time2-time1) / ((time1+time2) / 2) * 100
					print swimmer, event, time1, time2
					if abs(drop) > 10:  # toss outliers
						continue
					allImprovement[team][swimmer][event] = drop
					teamImprovement[team].append(drop)
		return allImprovement, teamImprovement

	allImprovement, teamImprovement = calcImprovement(top1, top2)

	if season3:  # combine in optional season 3
		allImprovement2, teamImprovement2 = calcImprovement(top2, top3)
		combined = teamImprovement.copy()
		for team in teamImprovement2:
			if team in combined:
				combined[team].extend(teamImprovement2[team])
			else:
				combined[team] = teamImprovement2[team]
		teamImprovement = combined

	if season4 and season3: # combine in optional season 4
		allImprovement2, teamImprovement2 = calcImprovement(top3, top4)
		combined = teamImprovement.copy()
		for team in teamImprovement2:
			if team in combined:
				combined[team].extend(teamImprovement2[team])
			else:
				combined[team] = teamImprovement2[team]
		teamImprovement = combined

	return teamImprovement, allImprovement

def improvement2(gender='Men', teams=MIAC, season1=thisSeason()-1, season2=thisSeason()-2):
	posSeasons = [2016, 2015, 2014, 2013, 2012, 2011]
	#print season1, season2
	if season1 > season2 and season1 in posSeasons and season2 in posSeasons:
		seasons = range(season2, season1)
		#print seasons
	teamImprovement = {}
	for swim in Improvement.select().where(Improvement.fromseason << seasons, Improvement.gender==gender,
								   Improvement.team << list(teams)):
		if swim.team not in teamImprovement:
			teamImprovement[swim.team] = []
		teamImprovement[swim.team].append(swim.improvement)

	if len(teams)==1 and teams[0] in teamImprovement:
		return teamImprovement[teams[0]]
	return teamImprovement

def timeHistograms():
	times = {'2008':[], '2009':[], '2010':[]}  # 2016 is the only season with all the times
	#times = {}
	#for season in range(2008, 2017):
	#	times[str(season)] = []
	for season in times:
		for swim in Swim.select(Swim.time).where(Swim.division=='D1', Swim.gender=='Women',
			Swim.event=='100 Yard Freestyle', Swim.season==int(season)).limit(3000).order_by(Swim.time):
			times[season].append(swim.time)
	#print len(times[season])

	plt.hist(times['2009'], 30, alpha=0.5, label='2009')
	plt.hist(times['2010'], 30, alpha=0.5, label='2010')
	plt.hist(times['2008'], 30, alpha=0.5, label='2008')

	plt.legend(loc='upper right')
	plt.show()

def timePlacePPts(place=100):
	points = {}
	for season in [2011, 2012, 2013, 2014]:
		points[season] = {}
		for divGen in [('Men', 'D1'), ('Men', 'D3'), ('Women', 'D1'), ('Women', 'D3')]:
			gender = divGen[0]
			division = divGen[1]
			points[season][division + gender] = {}
			for event in eventOrderInd:
				for swim in Swim.raw("select * from swim where event=%s and season=%s and division=%s and gender=%s order "
							 "by time limit 1 offset %s",
						 event, season, division, gender, place):
					print event, season, division, gender, place, swim.getPPTs()
					points[season][division + gender][event] = swim.getPPTs()
	for season in points:
		for divGen in points[season]:
			output = str(season) + ',' + divGen
			for event in eventOrderInd:
				output += ',' + str(round(points[season][divGen][event], 2))
			print output

def getConfMeets(season=2015, gender='Women', division='D1'):
	# find the meet where most best times come from for the whole conference
	allconfs = getConfs()[0]
	confs = allconfs[division][gender]
	confMeets = {}
	for conf in confs:
		if conf=='': continue
		for swim in Swim.raw("WITH topTimes AS (SELECT name, event, meet, time, row_number() OVER (PARTITION BY event,name "
				 "ORDER BY time) AS rnum "
				 "FROM Swim "
				 "WHERE conference=%s AND season=%s AND date > '%s-02-01' AND gender=%s) "
				 "SELECT name,event,meet,time FROM topTimes WHERE rnum=1",
				 conf, season, season, gender):
			if not conf in confMeets:
				confMeets[conf] = []
			confMeets[conf].append(swim.meet)
	taperMeets = {}
	for conf in confMeets:
		taperMeet = max(set(confMeets[conf]), key=confMeets[conf].count)
		taperMeets[conf] = taperMeet
	return taperMeets

def testMeetPrediction(sigmat=.005, sigmai=.005, gender='Women', division='D3', week=14):
	# evaluates the error on meet simulations
	print sigmat, sigmai, week

	# prediction categories, 10%, 20%...
	lumpedPre = {}
	lumps = range(0, 110, 10)
	for i in lumps:
		lumpedPre[str(i)] = []

	for season in [2016]:  # 2015, 2014, 2013, 2012]:
		# first find the taper meets
		conf_meets = self.getConfMeets(season, gender=gender, division=division)
		for conf in conf_meets:
			print conf, conf_meets[conf]
			conf_meet = Meet(name=conf_meets[conf], gender=gender)
			conf_meet.score()
			finalScores = conf_meet.teamScores()
			finalPlaces = [score[0] for score in finalScores]

			if week==-1:
				newMeet = self.conference(conf=conf, gender=gender, division=division, season=season-1, nextYear=True)
				probScores = newMeet.scoreMonteCarlo(sigma=sigmai, teamSigma=sigmat)
			else:
				newDate = conf_meet.date - timedelta(weeks=week)
				newMeet = self.conference(conf=conf, gender=gender, division=division, season=season,
				 dateStr=newDate)
				#newMeet = self.conference(conf=conf, gender=gender, division=division, season=season-1,
				# nextYear=True)
				newMeet.taper(weeks=16 - week)
				probScores = newMeet.scoreMonteCarlo(sigma=sigmai, teamSigma=sigmat)
				newMeet.reset(times=True)

			# evaluate the predictions
			for team in probScores:
				#print probScores, finalPlaces
				for idx, prob in enumerate(probScores[team]):
					rProb = str(int(round(prob, 1) * 100))
					if prob >= 1:  # make sure 0 predictions don't blow up
						prob = .99
					if prob <= 0:
						prob = .01
					if idx in finalPlaces and finalPlaces[idx] == team:  # correct prediction, log-based score
						score = log(prob)
					else:  # wrong
						score = log(1 - prob)
					lumpedPre[rProb].append(score)
	# now aggregate
	totalError = 0
	for percent in lumpedPre:
		totalError += sum(lumpedPre[percent])
	print 'Error:', totalError

	return -totalError

def nats_tapers(topTime=True):
	nats = Meet(name="2017 NCAA DI Men's")
	team_drops = {}
	print nats.date

	for taperSwim in nats.getSwims():
		# now find the top untapered swims before that date
		if topTime:
			for earlySwim in Swim.select(fn.min(Swim.time)).where(Swim.swimmer==taperSwim.swimmer,
				Swim.event==taperSwim.event, Swim.date < nats.date):
				if earlySwim.min:
					#print earlySwim.min, taperSwim.min, earlySwim.swimmer, earlySwim.swimmer
					dropPer = 100 * (earlySwim.min - taperSwim.time) / taperSwim.time
					if taperSwim.team not in team_drops:
						team_drops[taperSwim.team] = []
					team_drops[taperSwim.team].append(dropPer)
		# use average time
		else:
			for earlySwim in Swim.select(fn.avg(Swim.time)).where(Swim.swimmer==taperSwim.swimmer,
				Swim.event==taperSwim.event, Swim.date < nats.date):
				if earlySwim.avg:
					dropPer = 100 * (earlySwim.avg - taperSwim.time) / taperSwim.time
					if taperSwim.team not in team_drops:
						team_drops[taperSwim.team] = []
					team_drops[taperSwim.team].append(dropPer)

	for team in team_drops:
		if len(team_drops[team]) < 20:
			continue
		print team, np.mean(team_drops[team])

	# do drops cluster? No


def timedrops():
		timeDrops = {'Men': {}, 'Women': {}}
		dropDif = {'Men': {}, 'Women': {}}
		for season in [2008, 2009, 2010]:
			for rank in [1, 16, 200]:
				for swim in Swim.raw('SELECT event, time, gender, rank, name, meet, team, division, year FROM '
					'(SELECT name, time, event, meet, team, year, gender, division, rank() '
					'OVER (PARTITION BY gender, event, division ORDER BY time, name, meet) '
					'FROM swim '
					'WHERE swim.season = %s) AS a '
					'WHERE a.rank=%s order by gender, event ', season, rank):
					if swim.division != 'D3': continue
					if swim.event not in timeDrops[swim.gender]:
						timeDrops[swim.gender][swim.event] = {}
						dropDif[swim.gender][swim.event] = {}
					if str(rank) not in timeDrops[swim.gender][swim.event]:
						timeDrops[swim.gender][swim.event][str(rank)] = {}
						dropDif[swim.gender][swim.event][str(rank)] = {}
					if str(season) not in timeDrops[swim.gender][swim.event][str(rank)]:
						timeDrops[swim.gender][swim.event][str(rank)][str(season)] = {}
					timeDrops[swim.gender][swim.event][str(rank)][str(season)] = swim.time
				#print timeDrops

		improvements = []
		impStroke = {'Breastroke': [], 'Backstroke': [], 'Butterfly': [], 'Freestyle': [], 'IM': []}
		impGender = {'Men': [], 'Women': []}
		impDistance = {'50': [], '100': [], '200': [], 'distance': []}
		impRank = {'1': [], '16': [], '200': []}
		for gender in timeDrops:
			for event in timeDrops[gender]:
				for rank in timeDrops[gender][event]:
					time7 = timeDrops[gender][event][rank]['2008']
					time8 = timeDrops[gender][event][rank]['2009']
					time9 = timeDrops[gender][event][rank]['2010']

					perImp = ((time8 - (time7 + time9) / 2.0) / time8) * 100
					dropDif[gender][event][rank] = perImp
					improvements.append(perImp)
					if 'Breastroke' in event:
						impStroke['Breastroke'].append(perImp)
					elif 'Backstroke' in event:
						impStroke['Backstroke'].append(perImp)
					elif 'Butterfly' in event:
						impStroke['Butterfly'].append(perImp)
					elif 'Freestyle' in event:
						impStroke['Freestyle'].append(perImp)
					elif 'Individual Medley' in event:
						impStroke['IM'].append(perImp)

					impGender[gender].append(perImp)
					impRank[str(rank)].append(perImp)

					if '100' in event:
						impDistance['100'].append(perImp)
					elif '200' in event:
						impDistance['200'].append(perImp)
					elif event == '50 Yard Freestyle':
						impDistance['50'].append(perImp)
					elif '500 Yard' in event or '1650 Yard' in event or '400 Yard Individual Medley' in event:
						impDistance['distance'].append(perImp)

				print gender + ',' + event + ',' + str(round(np.mean(dropDif[gender][event].values()), 3))

		print np.mean(improvements)
		for gender in impGender:
			print gender, np.mean(impGender[gender])
		for stroke in impStroke:
			print stroke, np.mean(impStroke[stroke])
		for distance in impDistance:
			print distance, np.mean(impDistance[distance])
		for rank in impRank:
			print rank, np.mean(impRank[rank])

def taper_stats():
	import pandas as pd
	dates, drops, teams, names, seasons = [], [], [], [], []
	for team in ['Stanford', 'Texas', 'California', 'Michigan', 'Georgia', 'Florida', 'Auburn', 'Wisconsin',
		'Minnesota', 'Arizona', 'Northwestern']:
		gender = 'Men'
		for season in [2012, 2013, 2014, 2015, 2016]:
			texas = TeamSeason.get(season=season, gender=gender, team=team)
			for taper_swim in texas.getTaperSwims():
				for swim in Swim.select(Swim.time, Swim.name, Swim.date).where(Swim.swimmer==taper_swim.swimmer,
												Swim.event==taper_swim.event, Swim.gender==gender):
					ratio = swim.time/taper_swim.time
					if ratio < 1.2:
						drops.append(ratio)
						dates.append(pd.Timestamp(swim.date))
						teams.append(team)
						names.append(swim.name)
						seasons.append(season)

	data = pd.DataFrame({'drop': drops, 'date': dates, 'team': teams, 'name': names, 'seasons': season})
	'''
	import fbprophet
	m = fbprophet.Prophet(weekly_seasonality=False, n_changepoints=0)
	m.fit(ts)
	future = m.make_future_dataframe(periods=400)
	forecast = m.predict(future)

	#print forecast['yhat']
	#print forecast[['ds', 'yhat']]
	#m.plot(forecast)
	#m.plot_components(forecast)
	#df.hist('y')
	#plt.show()
	'''
	#print drops, dates, teams, names

	from statsmodels.formula.api import ols
	import statsmodels.api as sm
	import matplotlib.pyplot as plt

	data.to_csv("taper_stats_stan.csv")
	#data.boxplot(column='drop', by='name')
	#plt.show()
	#model = ols('drop ~ name', data=data).fit()
	#anova = sm.stats.anova_lm(model, typ=2)
	#print anova

# predict winning NCAA times for each year
def recordPrediction( event, division='D1', gender='Men', season=None):
	from scipy.stats import skewnorm
	import numpy as np

	season_adjust = False
	record_season = season
	p_season = season
	if season > 2018:
		season = 2018
		season_adjust = True
		record_season = None  # use all time records for future

	record = get_record(event, division, gender, season=record_season)
	# find top time dist
	times = []
	for swim in Swim.raw("(SELECT * FROM top_swim WHERE gender=%s and division=%s and event=%s and season=%s)"
							, gender, division, event, season):
		times.append(swim.time)

	#print event, division, gender, season, len(times)
	if len(times) == 0:
		return
	times = rejectOutliers(times, l=4, r=4)

	# best fit of data
	(mu, sigma) = norm.fit(times)
	(a, mu, sigma) = skewnorm.fit(times, max(times)-mu, loc=mu, scale=sigma)

	plot = True
	if plot:  # the histogram of the data
		import matplotlib.pyplot as plt
		n, bins, patches = plt.hist(times, 60, density=1)
		y = skewnorm.pdf(bins, a, mu, sigma)
		plt.plot(bins, y)
		plt.ylabel('% of times')
		plt.xlabel('Time in seconds')
		plt.savefig("100_free_men_dist.svg", format="svg")
		plt.show()

	# season adjustment if after current season
	if season_adjust:
		mu += season_imp(event, division, gender, p_season=p_season)

	dist = skewnorm(a, mu, sigma)

	sample = 1000
	top_times = []
	top = 0
	for i in range(sample):
		topTime = min(dist.rvs(size=int(len(times))))
		top_times.append(topTime)
		if topTime < record:
			top += 1
	mu = np.median(top_times)

	if plot:  # the histogram of the data
		import matplotlib.pyplot as plt
		n, bins, patches = plt.hist(top_times, 60, density=1)
		plt.ylabel('% of times')
		plt.xlabel('Time in seconds')
		plt.savefig("100_free_men_winning_dist.svg", format="svg")
		plt.show()

	return swimTime(record), swimTime(mu), top / float(sample)

def get_record(event, division='D1', gender='Men', season=2018):
	if season:
		for swim in Swim.select(fn.min(Swim.time)).where(Swim.division==division, Swim.gender==gender,
												 Swim.event==event, Swim.season==season):
			return swim.min
	else:
		for swim in Swim.select(fn.min(Swim.time)).where(Swim.division==division, Swim.gender==gender,
												 Swim.event==event):
			return swim.min

# linear fit to predict future event improvements
def season_imp(event, division='D1', gender='Men', p_season=2019):
		seasons, avg_times = [], []
		time_2018 = None
		for swim in Swim.raw("SELECT event, season, avg(time) from "
			"(SELECT event, season, time FROM top_swim WHERE gender=%s and division=%s and event=%s and season>2009)) "
			"GROUP BY season, event ", gender, division, event):
			seasons.append(swim.season)
			avg_times.append(swim.avg)
			if swim.season == 2018:
				time_2018 = swim.avg

		slope, intercept, r_value, p_value, std_err = linregress(seasons, avg_times)

		return intercept + slope * p_season - time_2018

if __name__=='__main__':
	taper_stats()
	#recordPrediction(event='100 Free', season=2019)
