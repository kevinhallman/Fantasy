import numpy as np
from datetime import date as Date, timedelta
import datetime
import peewee
import os, urlparse, time, json
#from scipy.stats import norm, linregress
#simport matplotlib.pyplot as plt

from swimdb import Improvement, TeamSeason, Swimmer, Swim, Meet, week2date, date2week, thisSeason, rejectOutliers
from events import eventOrderInd, eventsChamp3, eventsChamp, eventsDualS, requiredEvents, allEvents, eventOrder

pointsChampionship = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
pointsDualI = [9, 4, 3, 2, 1]
pointsDualR = [11, 4, 2]

# setup database connection
db_proxy = peewee.Proxy()
db = peewee.Proxy()

def ECDF(data):
	def cdf(num):
		d = data
		l = float(len(d))
		return (sum(1 for i in d if i < num) + sum(.5 for i in d if i==num))/l
	return cdf

# retrieves all conference affiliations
def getConfs():
	confs = {'D1': {'Men': {}, 'Women': {}}, 'D2': {'Men': {}, 'Women': {}}, 'D3': {'Men': {}, 'Women': {}}}
	allTeams = {'Men': {'D1': set(), 'D2': set(), 'D3': set()}, 'Women': {'D1': set(), 'D2': set(), 'D3': set()}}
	for newTeam in TeamSeason.select(TeamSeason.team, TeamSeason.conference, TeamSeason.division,
									 TeamSeason.gender).distinct(TeamSeason.team):
		if newTeam.conference not in confs[newTeam.division][newTeam.gender]:
			confs[newTeam.division][newTeam.gender][newTeam.conference] = set()

		confs[newTeam.division][newTeam.gender][newTeam.conference].add(newTeam.team.strip())
		allTeams[newTeam.gender][newTeam.division].add(newTeam.team.strip())

	for division in ['D1', 'D2', 'D3']:
		allTeams['Men'][division] = list(allTeams['Men'][division])
		allTeams['Men'][division].sort()
		allTeams['Women'][division] = list(allTeams['Women'][division])
		allTeams['Women'][division].sort()

	return confs, allTeams

def nextYear(year):
	if year=='Freshman':
		return 'Sophomore'
	if year=='Sophomore':
		return 'Junior'
	if year=='Junior':
		return 'Senior'
	return None

def grad(f, x, y, h=0.0025):
	dx = (f(x, y) - f(x+h, y))/h
	dy = (f(x, y) - f(x, y+h))/h
	return dx, dy

def gradientDescent(f, x0, y0, steps=10, step=.001):
	for _ in range(steps):
		dx, dy = grad(f, x0, y0)
		length = ((dx**2 + dy**2) ** .5)
		print 'delta:', dx, dy
		x0 += step * dx / length
		y0 += step * dy / length
		if x0 < 0:
			x0 = 0.001
		if y0 < 0:
			y0 = 0.001
		#print x0, y0
	return x0, y0

def frange(x, y, jump):
	while x < y:
		yield x
		x += jump

'''
full database methods
'''

'''
creates a swim meet with given teams and meets format is [(team1,meet1),(team2,meet2),...]
'''
def swimMeet(teamMeets, gender=None, includeEvents='all', excludeEvents=set(),
			 selectEvents=True, resetTimes=False, verbose=False):
	meet = Meet()
	teams = []

	if includeEvents == 'all':
		includeEvents = allEvents

	commonEvents = allEvents  # start with all events and whittle down
	for teamMeet in teamMeets:
		newTeam = teamMeet['team']
		newMeet = teamMeet['meet']
		if 'season' in teamMeet:
			season = teamMeet['season']
		else:
			season = None

		if verbose: print isinstance(newMeet, basestring)
		if isinstance(newMeet, basestring):  # just a name
			newMeet = Meet(name=newMeet, gender=gender, teams=[newTeam], season=season, topSwim=True)
		commonEvents = commonEvents & set(newMeet.eventSwims.keys())
		if verbose: print season, newMeet, newTeam
		if verbose: print newMeet.eventSwims

		# resolve duplicate names, first try season, then a number
		newTeamName = None
		if teams.count(newTeam) > 0:
			newTeamName = newTeam + ' ' + season
			if teams.count(newTeamName) > 0:
				newTeamName += ' ' + str(teams.count(newTeamName))
		if newTeamName:
			teams.append(newTeamName)
		else:
			teams.append(newTeam)
		# now apply to existing swims
		for swim in newMeet.getSwims(newTeam):
			if newTeamName:
				swim.scoreTeam = newTeamName
			meet.addSwim(swim)

	if verbose: print meet

	meet.reset(times=resetTimes)

	if len(meet.teams) == 2:
		if selectEvents:
			meet.topEvents(25, 3, 4)
			'''need to fix event selection for dual meets'''
		meet.events = (commonEvents | includeEvents) - excludeEvents
		meet.score(dual=True)
	else:
		if selectEvents:
			meet.topEvents()
		meet.events = eventsChamp3
		meet.score()

	return meet

'''
optimal lineup creator
'''
def lineup(teams, meet, resetTimes=False, events=None, gender='Men'):
	if events:
		meet.events = events
	teamNames = []

	for teamName in teams:
		division = teams[teamName]['division']
		if not 'season' in teams[teamName]:
			season = thisSeason()
		else:
			season = teams[teamName]['season']

		# add each team's top times to meet
		team = TeamSeason.get(season=season, team=teamName, gender=gender, division=division)  # need division
		topTimesMeet = team.topTimes(events=events)

		# resolve duplicate names, first try season, then a number
		newTeamName = None
		if teamNames.count(teamName) > 0:
			newTeamName = teamName + ' ' + season
			if teamNames.count(newTeamName) > 0:
				newTeamName += ' ' + str(teamNames.count(newTeamName))

		if newTeamName:
			teamNames.append(newTeamName)
		else:
			teamNames.append(teamName)

		for swim in topTimesMeet.getSwims():
			if newTeamName:
				swim.scoreTeam = newTeamName
			meet.addSwim(swim)

	meet.reset(times=resetTimes)
	meet.place()

	# lineup optimize if creating lineup for just one team
	if len(teamNames) == 1:
		meet.lineup(teamNames.pop())
	else:
		meet.topEvents(17, indMax=3)

	return meet

'''
top expected score for the whole team
'''
def topTeamScore(teamName, dual=True, season=thisSeason(), gender='Men', division='D3', weeksIn=None):
	# convert the week to a date
	simDate = week2date(weeksIn, season)

	# cache off times?
	if dual:
		events = eventsDualS
	else:
		events = eventsChamp
	team = TeamSeason.get(season=season, team=teamName, gender=gender, division=division)  # need division
	topMeet = team.topTimes(events=events, dateStr=simDate)

	topMeet.topEvents(teamMax=17, indMax=3)
	if dual:
		scores = topMeet.expectedScores(swimmers=6, division=division)
	else:
		scores = topMeet.expectedScores(swimmers=16, division=division)

	if team in scores:
		return scores[team]
	return 0

'''
returns meet of average times
'''
def averageTimes(conf, season=None, gender='Men', division=None, date=None):
	if type(date) == type(str):
		date = Date(date)
	if not season:
		season = thisSeason()  # use current season
	if not date:
		date = Date.today()

	topMeet = Meet()
	topMeet.date = date
	if conf=='Nationals':
		select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason)\
			.where(TeamSeason.gender==gender, TeamSeason.division==division, TeamSeason.season==season, Swim.date < date)
	else:
		select = Swim.select(Swim, Swimmer, TeamSeason).join(Swimmer).join(TeamSeason)\
			.where(TeamSeason.gender==gender, TeamSeason.conference==conf, TeamSeason.season==season, Swim.date < date)

	query = select.select(Swim.name, Swim.event, peewee.fn.Avg(Swim.time), Swim.team, Swimmer.year).group_by(Swim.name,
			Swim.event, Swim.team, Swimmer.year)

	for swim in query:
		time = swim.avg
		if swim.event != '1000 Free':
			newSwim = Swim(name=swim.name, event=swim.event, time=time, gender=gender, team=swim.team,
				season=season, year=swim.swimmer.year, swimmer=swim.swimmer)
			topMeet.addSwim(newSwim)

	topMeet.place()
	return topMeet

'''
returns meet of top times, start with top 75 in each event
'''
def topTimes(season, gender, conf, division=None, dateStr=None, limit=75):
	newMeet = Meet()
	newMeet.date = dateStr
	if not dateStr:
		if conf == 'Nationals':
			query = Swim.raw("SELECT event, time, name, team, date, year, meet, swimmer_id, rank FROM ( "
					"SELECT event, time, name, team, date, year, meet, swimmer_id, division, season, gender, rank() "
					"over (Partition BY event ORDER BY event, time) FROM top_swim "
					"WHERE season=%s and gender=%s and division=%s) ts WHERE rank<%s",
					season, gender, division, limit)
		else:
			query = Swim.raw("SELECT event, time, name, team, date, year, meet, swimmer_id, rank FROM ( "
					"SELECT event, time, name, team, date, year, meet, swimmer_id, division, season, gender, rank() "
					"over (Partition BY event ORDER BY event, time) "
					"FROM top_swim WHERE season=%s and gender=%s and conference=%s) ts WHERE rank<%s",
					season, gender, conf, limit)
	else:
		if conf == 'Nationals':
			query = Swim.raw("SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM "
			"(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() "
			"OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) "
			"FROM (swim "
				"INNER JOIN swimmer sw ON swim.swimmer_id=sw.id "
				"INNER JOIN teamseason ts ON sw.team_id=ts.id) "
				"WHERE ts.season=%s and ts.gender=%s and ts.division=%s and swim.date<%s "
			") AS a "
			"WHERE a.rank=1", season, gender, division, dateStr)
		else:
			query = Swim.raw("SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM "
			"(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() "
			"OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) "
			"FROM (swim "
				"INNER JOIN swimmer sw ON swim.swimmer_id=sw.id "
				"INNER JOIN teamseason ts ON sw.team_id=ts.id) "
				"WHERE ts.season=%s and ts.gender=%s and ts.division=%s and swim.date<%s and ts.conference=%s"
			") AS a "
			"WHERE a.rank=1", season, gender, division, dateStr, conf)
	
	for swim in query:
		swim.gender = gender
		swim.division = division
		swim.conference = conf
		swim.season = season
		newMeet.addSwim(swim)
	if '1000 Free' in newMeet.eventSwims:
		del(newMeet.eventSwims['1000 Free'])

	return newMeet

# simulates conference or national meet, must be real conference
def sim_conference(season, gender, conf, division, dateStr=None, top=True, update=False, taper=False, teamMax=17, verbose=False):
	swimmer_limit = 100
	if not season: # use current season
		season = thisSeason()

	# estimated taper meet
	if taper:
		if not dateStr:
			dateStr = Date.today()
		if type(dateStr) == str:
			dateStr = datetime.datetime.strptime(dateStr, '%Y-%m-%d').date()
		
		week = date2week(dateStr)
		if verbose: print week

		if week > 1:
			conf_meet = topTimes(conf=conf, season=season, gender=gender, division=division, limit=swimmer_limit)
			conf_meet.taper(week=week, division=division, gender=gender)
		else:
			conf_meet = topTimes(conf=conf, season=season-1, gender=gender, division=division, limit=swimmer_limit)
			conf_meet.remove_class('Senior')
	else:
		if top:
			conf_meet = topTimes(conf=conf, season=season, gender=gender, division=division, dateStr=dateStr, limit=swimmer_limit)
		else:  # use avg times
			conf_meet = averageTimes(conf=conf, season=season, gender=gender, division=division, date=dateStr)

	conf_meet.events = eventsChamp3
	conf_meet.topEvents(teamMax=teamMax)
	conf_meet.score()
	
	if verbose:
		print 'conf sim', conf, season, dateStr
		print conf_meet
		print conf_meet.teamScores()

	if update:
		if conf == 'Nationals':
			nats = True
		else:
			nats = False
		# update the season after you take times from
		conf_meet.update(division=division, gender=gender, season=season, nats=nats, taper=taper, week=week)

	return conf_meet

'''
returns top 25 teams by est invite strength. Don't worry about taper since strength isn't tapered
'''
def teamRank(division='D3', gender='Men', season=2016, num=25):
	teams = []
	for team in TeamSeason.raw('SELECT rank_filter.* FROM ( '
		'SELECT teamseason.*, teamstats.strengthinvite as strength, rank() OVER ( '
			'PARTITION BY teamseason.id '
			'ORDER BY teamstats.week DESC '
		') '
		'FROM teamseason '
		'INNER JOIN teamstats ON teamseason.id=teamstats.team_id '
		'WHERE gender=%s and division=%s and season=%s and teamstats.strengthinvite IS NOT NULL '
		') rank_filter WHERE rank=1 ORDER BY strength DESC LIMIT %s', gender, division, season, num):
		teams.append(team)
	return teams
'''
Returns top swimmers in a conference by top 3 event ppts
'''
def swimmerRank(division='D3', gender='Men', season=2019, num=25, conference=None):
	# make sure all ppts are saved to the db
	if not conference:  # all conferences
		for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,
						TeamSeason.division==division, TeamSeason.season==season, Swimmer.ppts.is_null()):
			swimmer.getPPTs()
	else:
		for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,
				TeamSeason.division==division, TeamSeason.season==season, TeamSeason.conference==conference,
				Swimmer.ppts.is_null()):
			swimmer.getPPTs()

	# return sorted list of top swimmers
	swimmers = []
	if not conference:  # all conferences
		for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,
				TeamSeason.division==division, TeamSeason.season==season,
				Swimmer.ppts.is_null(False)).order_by(Swimmer.ppts.desc()).limit(num):
			swimmers.append(swimmer)
	else:
		for swimmer in Swimmer.select(Swimmer, TeamSeason).join(TeamSeason).where(Swimmer.gender==gender,
				TeamSeason.division==division, TeamSeason.season==season, Swimmer.ppts.is_null(False),
				TeamSeason.conference==conference).order_by(Swimmer.ppts.desc()).limit(num):
			swimmers.append(swimmer)

	return swimmers


def update_weekly_stats(week=None, division='D3', gender='Women', season=2018):
	if not week:
		week = date2week(Date.today())
	simDate = week2date(week, season=season)

	print 'season', season, 'week', week, 'date', simDate
	if simDate > Date.today():
		print 'Error, future date'
		return

	# national meets probabilities
	sim_conference(conf='Nationals', gender=gender, division=division, season=season, update=True, dateStr=simDate, taper=True)

	# conf meet odds
	conferences, _ = getConfs()

	for conference in conferences[division][gender]:
		if conference == '':
			continue
		sim_conference(conf=conference, gender=gender, season=season, division=division, update=True, dateStr=simDate, taper=True)

	# update team strengths
	for team in TeamSeason.select().where(TeamSeason.division==division, TeamSeason.gender==gender, TeamSeason.season==season):
		team.getWeekStrength(update=True, weeksIn=week, verbose=True)

'''
returns which meets were likely tapers
'''
def taperMeets(year=2015, gender='Women', division='D1'):  # find meets where most best times come from
	teamMeets = {}
	#teams=['Univ of Utah', 'Stanford', 'California', 'Arizona', 'Southern Cali', 'Arizona St']
	_, allTeams = getConfs()
	teams = allTeams[gender][division]
	for team in teams:
		for swim in Swim.raw("SELECT * FROM top_swim WHERE team=%s AND season=%s AND date > '%s-02-01' AND "
							 "gender=%s) ", team, year, year, gender):
			if not team in teamMeets:
				teamMeets[team] = []
			teamMeets[team].append(swim.meet)

	# count number of teams tapered at each meet
	taperMeets = {}
	for team in teamMeets:
		taperMeet = max(set(teamMeets[team]), key=teamMeets[team].count)
		if taperMeet not in taperMeets:
			taperMeets[taperMeet] = 0
		taperMeets[taperMeet] += 1

	bigTaperMeets = [i for i in taperMeets if taperMeets[i]>2]
	return bigTaperMeets


'''
returns improvemnt data from db, from season1 to season2
'''
def getImprovement(gender='Men', teams=['Carleton'], season1=thisSeason()-1, season2=thisSeason()-2):
	posSeasons = [2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011]
	#print season1, season2
	if season1 > season2 and season1 in posSeasons and season2 in posSeasons:
		seasons = range(season2, season1)
		#print seasons
	else:
		return
	teamImprovement = {}
	for swim in Improvement.select().where(Improvement.fromseason << seasons, Improvement.gender==gender,
								   Improvement.team << list(teams)):
		if swim.team not in teamImprovement:
			teamImprovement[swim.team] = []
		teamImprovement[swim.team].append(swim.improvement)

	if len(teams)==1 and teams[0] in teamImprovement:
		return teamImprovement[teams[0]]
	return teamImprovement

'''
calculates and stores improvement data for a season
'''
def storeImprovement(season=2018):
	swims = []
	for team in TeamSeason.select().where(TeamSeason.season==season):
		preTeam = team.getPrevious()
		if not preTeam:
			continue
		print team.team
		print preTeam.team

		top1 = team.getTaperSwims(structured=True)
		#print top1
		top2 = preTeam.getTaperSwims(structured=True)
		#print top2

		for swimmer in top1:
			if not swimmer in top2:
				continue
			for event in top1[swimmer]:
				if not event in top2[swimmer]:
					continue
				swim1 = top1[swimmer][event]
				swim2 = top2[swimmer][event]
				time1 = swim1.time
				time2 = swim2.time
				drop = (time2-time1) / ((time1+time2) / 2) * 100
				#print swimmer, event, time1, time2
				if abs(drop) > 10:  # toss outliers
					continue

				newSwim = {'fromseason': season-1, 'toseason': season, 'name': swim1.name,
						   'fromyear': swim2.year, 'toyear': swim1.year,
						   'team': team.team, 'gender': team.gender, 'event': event,
						   'improvement': drop,  # positive=faster
						   'fromtime': swim2.time, 'totime': swim1.time,
						   'conference': team.conference, 'division': team.division}
				query = Improvement.select().where(Improvement.name==swim1.name, Improvement.event==swim1.event,
												   Improvement.team==swim1.team, Improvement.fromseason==season-1)
				if not query.exists():
					swims.append(newSwim)

	print len(swims)
	db.connect()
	for i in range(len(swims) / 1000):
		print i
		with db.transaction():
			Improvement.insert_many(swims[i*1000:(i+1)*1000]).execute()


def update_season_stats(season=2018, recalc=True):
	if recalc:
		print 'storing improvement'
		storeImprovement(season)

	for team in TeamSeason.select().where(TeamSeason.season==season):
		print team.team
		team.updateSeasonStats()


def time_drops_data(season, team, gender='Men', division='D1', verbose=False):
	import pandas as pd
	swims = []
	team_adjustments,team_adjustments2 = {}, {}
	for team in TeamSeason.select().where(TeamSeason.gender==gender, TeamSeason.division==division, 
					TeamSeason.season == season):
		preTeam = team.getPrevious()
		if not preTeam:
			continue
		if verbose: print team.team, preTeam.team

		top1 = team.getTaperSwims(structured=True)
		top2 = preTeam.getTaperSwims(structured=True)
		if verbose: print top1, top2

		for swimmer in top1:
			if not swimmer in top2:
				continue
			for event in top1[swimmer]:
				if not event in top2[swimmer]:
					continue
				swim1 = top1[swimmer][event]
				swim2 = top2[swimmer][event]
				time1 = swim1.time
				time2 = swim2.time
				drop = (time2-time1) / ((time1+time2) / 2) * 100
				if verbose: print swimmer, event, time1, time2
				if abs(drop) > 10:  # toss outliers
					continue

				for week in [10, 20]:
					date = week2date(week, season)
					if verbose: print swim1.swimmer.id, event, date
					for swim in Swim.select(peewee.fn.min(Swim.time)).where(Swim.swimmer==swim1.swimmer, Swim.event==event, Swim.date<date):
						if week == 10:
							week10s2 = swim.min
						elif week == 20:
							week20s2 = swim.min
				for week in [10, 20]:
					date = week2date(week, season -1)
					for swim in Swim.select(peewee.fn.min(Swim.time)).where(Swim.swimmer==swim2.swimmer, Swim.event==event, Swim.date<date):
						if week == 10:
							week10s1 = swim.min
						elif week == 20:
							week20s1 = swim.min
				totime = None
				for swim in Swim.select(peewee.fn.min(Swim.time)).where(Swim.swimmer==swim1.swimmer, Swim.event==event, Swim.date>date):
					totime = swim.min

				newSwim = {'name': swim1.name,
						   'team': team.team, 'gender': team.gender, 'event': event,
						   'improvement': drop,  # positive=faster
						   'fromtime': swim2.time, 'totime': totime,
						   'fromseason': preTeam.season,
						   'toseason': team.season,
						   'conference': team.conference, 'division': team.division,
						   'week10s1': week10s1,
						   'week20s1': week20s1,
						   'week10s2': week10s2,
						   'week20s2': week20s2}
				swims.append(newSwim)

	data = pd.DataFrame({'old_adj': team_adjustments.values(), 'new_adj': team_adjustments2.values()})
	from statsmodels.formula.api import ols
	model = ols('old_adj ~ new_adj', data=data).fit()
	print model.summary()
	
	return team_adjustments, team_adjustments2
	data = pd.DataFrame(swims)

	data.to_csv("stats/men_taper_stats.csv")


def nats_time_drops(gender='Men', division='D3', outfile='stats/all_taper_stats', verbose=False):
	import pandas as pd
	swims = []
	for season in range(2012, 2019):
		date = week2date(week=25, season=season)
		print date, season, gender, division, len(swims)
		conf = sim_conference(season, gender=gender, conf='Nationals', division=division, dateStr=date)
		conf.score()
		#team_adjustments, team_adjustments2 = {}, {}
		for event in conf.eventSwims:
			print event
			for swim in conf.eventSwims[event]:
				# just using scoring swims
				#if swim.score < 1: continue
				
				swimmer = swim.getSwimmer()
				if verbose: print swimmer.name, swimmer.name, event
				
				times = {}
				for seasons_back in range(4):
					temp_swimmer = swimmer.nextSeason(-seasons_back)
					#print temp_swimmer.name, temp_swimmer.year
					if not temp_swimmer: 
						times[seasons_back] = [None] * 25
						continue
					times[seasons_back] = []
					for week in range(1, 26):
						date = week2date(week=week, season=(season - seasons_back))
						#print date, week, season - seasons_back
						times[seasons_back].append(temp_swimmer.topTime(event=swim.event, date=date))

				newSwim = {'name': swimmer.name,
							'team': swimmer.team.team, 
							'gender': gender, 
							'event': event,
							'season': season,
							'place': swim.place,
							#'team_drop': swimmer.team.getTaperStats()[0]
							}
				for season_num in times:
					for num, time in enumerate(times[season_num]):
						newSwim['season' + str(season_num) + 'week' + str(num)] = time
				#print newSwim
				swims.append(newSwim)
		print len(swims)
	data = pd.DataFrame(swims)
	data.to_csv('{0}_{1}_{2}.csv'.format(outfile, division, gender))


def save_nats_drop_stats(file_name='model_params.json'):
	import pandas as pd
	from statsmodels.formula.api import ols
	
	data_d1_men = pd.read_csv('nats_taper_stats_D1_men.csv')
	data_d1_women = pd.read_csv('nats_taper_stats_D1_women.csv')
	data_d2_men = pd.read_csv('nats_taper_stats_D2_men.csv')
	data_d2_women = pd.read_csv('nats_taper_stats_D2_women.csv')
	data_d3_men = pd.read_csv('nats_taper_stats_D3_men.csv')
	data_d3_women = pd.read_csv('nats_taper_stats_D3_women.csv')
	
	fits = {}
	for gender in ['Women', 'Men']:
		fits[gender] = {}
		for division in ['D1', 'D2', 'D3']:
			
			if gender == 'Men':
				if division == 'D1':
					data = data_d1_men
				if division == 'D2':
					data = data_d2_men
				if division == 'D3':
					data = data_d3_men
			if gender == 'Women':
				if division == 'D1':
					data = data_d1_women
				if division == 'D2':
					data = data_d2_women
				if division == 'D3':
					data = data_d3_women
					
			fits[gender][division] = {}
			for week in range(25):
				fits[gender][division][week] = {}
				
				fits[gender][division][week]['one_season'] = {}
				fit_str = 'season0week24 ~ season0week{0} - 1'.format(week)
				model = ols(fit_str, data=data).fit()
				fits[gender][division][week]['one_season'] = model.params[0]
				
				fits[gender][division][week]['two_season'] = {}
				fit_str = 'season0week24 ~ season0week{0} + season1week24 - 1'.format(week)
				model = ols(fit_str, data=data).fit()
				fits[gender][division][week]['two_season'] = [model.params[0], model.params[1]]
				
				fits[gender][division][week]['three_season'] = {}
				fit_str = 'season0week24 ~ season0week{0} + season1week24 + season2week24 - 1'.format(week)
				model = ols(fit_str, data=data).fit()
				fits[gender][division][week]['three_season'] = [model.params[0], model.params[1], model.params[2]]
				
	print 'season0weekx', 'season1week24', 'season2week24'
	with open(file_name, 'w') as f:
		f.write(json.dumps(fits))

def save_taper_stats(division, gender, season):
	for team in TeamSeason.select().where(TeamSeason.division==division, TeamSeason.gender==gender, TeamSeason.season==season):
		for week in {4, 6, 8, 10, 12, 14, 16, 18, 20}:
			team.findTaperStats(topTime=True, averageTime=True, weeks=week)

if __name__ == "__main__":
	# database setup
	urlparse.uses_netloc.append("postgres")
	if "DATABASE_URL" in os.environ:  # production
		url = urlparse.urlparse(os.environ["DATABASE_URL"])
		db = peewee.PostgresqlDatabase(database=url.path[1:],
								user=url.username,
								password=url.password,
								host=url.hostname,
								port=url.port)
	else:
		db = peewee.PostgresqlDatabase('swimdb', user='hallmank')

	#nats_time_drops(gender='Men', division='D3')
	#update_weekly_stats(division='D1', gender='Men')

	for gender in ['Men', 'Women']:
		for season in [2018, 2017]:
			for division in ['D1', 'D2', 'D3']:
				save_taper_stats(gender=gender, division=division, season=season)
				#for week in range(25):
				#simDate = week2date(week=week, season=season)
				#conf = sim_conference(conf='Nationals', gender=gender, division=division, season=season, update=True, dateStr=simDate, taper=True)
				
	#conf = sim_conference(conf='MIAC', gender='Men', division='D3', season=2019, update=False, taper=True, verbose=False)
	#print conf
	