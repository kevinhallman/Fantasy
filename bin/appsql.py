#!/usr/bin/env python

import web
import sqlmeets
import re
import json
import os, urlparse
import numpy
from peewee import *
from swimdb import swimTime
from swimdb import Meet, TeamMeet, Team, TeamSeason
from operator import itemgetter
import time as Time

eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay"]
eventOrderInd = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley"]

urls = ('/', 'Home',
	'/home', 'Home',
	'/swimulate', 'Swimulate',
	'/swimulateJSON', 'SwimulateJSON',
	'/conference', 'Conf',
	'/conferenceJSON', 'ConfJSON',
	'/times', 'Times',
	'/placing', 'Placing',
	'/improvement', 'Improvement',
	'/improvementJSON', 'ImprovementJSON',
	'/rankings', 'Rankings',
	'/teamMeets', 'teamMeets',
	'/getConfs', 'getConfs',
	'/getTeams', 'getTeams',
	'/programs', 'Programs',
	'/programsJSON', 'ProgramsJSON',
	'/preseason', 'SeasonRankings',
	'/teamstats/(.+)', 'TeamStats'
)

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

def connection_processor(handler):
	db.connect()
	try:
		return handler()
	finally:
		if not db.is_closed():
			db.close()

def getConfs():
	confs = {'D1': {'Men': {}, 'Women': {}}, 'D2': {'Men': {}, 'Women': {}}, 'D3': {'Men': {}, 'Women': {}}}
	allTeams = {'Men': {'D1': [], 'D2': [], 'D3': []}, 'Women': {'D1': [], 'D2': [], 'D3': []}}
	for newTeam in TeamSeason.select(TeamSeason.team, TeamSeason.conference, TeamSeason.division,
									 TeamSeason.gender).distinct(TeamSeason.team):
		if newTeam.conference not in confs[newTeam.division][newTeam.gender]:
			confs[newTeam.division][newTeam.gender][newTeam.conference] = set()

		confs[newTeam.division][newTeam.gender][newTeam.conference].add(newTeam.team)
		allTeams[newTeam.gender][newTeam.division].append(newTeam.team)

		for division in ['D1', 'D2', 'D3']:
			allTeams['Men'][division].sort()
			allTeams['Women'][division].sort()
	return confs, allTeams

def getMeetList():
	newList = {'Men': {'D1': {}, 'D2': {}, 'D3': {}}, 'Women': {'D1': {}, 'D2': {}, 'D3': {}}}
	for teamMeet in TeamMeet.select(Meet, TeamMeet, TeamSeason).join(Meet).switch(TeamMeet).join(TeamSeason):
		newTeam = teamMeet.team.team
		gender = teamMeet.team.gender
		newSeason = teamMeet.team.season
		newMeet = teamMeet.meet.meet
		newDiv = teamMeet.team.division
		if newTeam not in newList[gender][newDiv]:
			newList[gender][newDiv][newTeam] = {}
		if newSeason not in newList[gender][newDiv][newTeam]:
			newList[gender][newDiv][newTeam][newSeason] = []
		newList[gender][newDiv][newTeam][newSeason].append(re.sub('\"', '\\\\\"', newMeet))
	return newList

web.config.debug = False
app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'gender': 'Women', 'division': 'D1'})
render = web.template.render('templates/', base="layout", globals={'context': session})

app.add_processor(connection_processor)

database = sqlmeets.SwimDatabase(database=db)
meetList = getMeetList()
(conferences, allTeams) = getConfs()

# appends the gender and division to the URL and allows them to be changed via there as well
def setGenDiv(gender, division):
	# modifies the URL if different
	if gender in ['Men', 'Women']:
		session.gender = gender
	if division in ['D1', 'D2', 'D3']:
		session.division = division

	if gender is None:
		print gender, division, session.gender, session.division, web.http.changequery(gender=session.gender, division=session.division)
		raise web.seeother(web.http.changequery(gender=session.gender))
	if division is None:
		raise web.seeother(web.http.changequery(division=session.division))

class Home():
	def GET(self):
		form = web.input(gender=session.gender, division=session.division)
		setGenDiv(form.gender, form.division)
		return render.home()

class Swimulate():
	def GET(self):
		form = web.input(team1=None, team2=None, meet1=None, meet2=None, _unicode=False, gender=None, division=None)
		setGenDiv(form.gender, form.division)

		gender = session.gender
		divTeams = allTeams[gender]

		if not form.team1:
			return render.swimulator(divTeams=divTeams, scores=None, teamScores=None, finalScores=None, winTable=None)

		keys = form.keys()
		
		formMeets = {}
		for key in keys:
			if key in ['gender', 'division']: continue
			num = int(key[-1])
			if not num in formMeets:
				formMeets[num] = [None, None, None, None]
			if "team" in key:
				formMeets[num][0] = form[key]
			elif "meet" in key:
				formMeets[num][1] = form[key]
			elif "season" in key:
				formMeets[num][3] = form[key]

		#use topDual if no meet?
		remove = set()
		optimizeTeams = {}
		for num in formMeets:
			tm = formMeets[num]
			if not tm[0] or not tm[1]:
				remove.add(num)
			elif tm[1] == 'Create Lineup':
				optimizeTeams[tm[0]] = int(tm[3])
				remove.add(num)
		for tm in remove:
			del(formMeets[tm])

		#print optimizeTeams

		if len(formMeets) + len(optimizeTeams) < 1:
			return render.swimulator(divTeams=divTeams, scores=None, teamScores=None, finalScores=None, winTable=None)
		
		else:
			newMeet = database.swimMeet(formMeets.values(), gender=gender, includeEvents=sqlmeets.requiredEvents,
										selectEvents=False, resetTimes=True)
			if optimizeTeams:
				newMeet = database.lineup(optimizeTeams, newMeet, gender=gender)
			if len(formMeets) > 2:  # show only six swims
				showNum = 20
			else:
				showNum = 6
			scores = newMeet.scoreString(showNum=showNum)
			teamScores = newMeet.scoreReport()
			newMeet.reset(True, True)

			winProb = newMeet.scoreMonteCarlo()
			winTable = showWinTable(winProb)
			return render.swimulator(divTeams=divTeams, scores=showMeet(scores), teamScores=showTeamScores(
				teamScores), finalScores=showScores(scores), winTable=winTable)

class SwimulateJSON():
	def GET(self):
		form = web.input(team1=None, team2=None, meet1=None, meet2=None, _unicode=False, gender=None, division=None)
		web.header("Content-Type", "application/json")
		gender = form.gender
		if not form.team1:
			return {}

		keys = form.keys()

		formMeets = {}
		for key in keys:
			if key in ['gender', 'division']: continue
			num = int(key[-1])
			if not num in formMeets:
				formMeets[num] = [None, None, None, None]
			if "team" in key:
				formMeets[num][0] = form[key]
			elif "meet" in key:
				formMeets[num][1] = form[key]
			elif "season" in key:
				formMeets[num][3] = form[key]

		# use topDual if no meet?
		remove = set()
		optimizeTeams = {}
		for num in formMeets:
			tm = formMeets[num]
			if not tm[0] or not tm[1]:
				remove.add(num)
			elif tm[1] == 'Create Lineup':
				optimizeTeams[tm[0]] = int(tm[3])
				remove.add(num)
		for tm in remove:
			del(formMeets[tm])

		if len(formMeets) + len(optimizeTeams) < 1:
			return {}
		else:
			newMeet = database.swimMeet(formMeets.values(), gender=gender, includeEvents=sqlmeets.requiredEvents,
										selectEvents=False, resetTimes=True)
			if optimizeTeams:
				newMeet = database.lineup(optimizeTeams, newMeet, gender=gender)
			if len(formMeets) > 2:  # show only six swims
				showNum = 20
			else:
				showNum = 6
			scores = newMeet.scoreString(showNum=showNum)
			teamScores = newMeet.scoreReport()
			newMeet.reset(True, True)
			winProb = newMeet.scoreMonteCarlo()

		labeledScores = JSONScores(scores)
		response = {}
		response['individual results'] = labeledScores
		response['team scores'] = teamScores
		response['win probability'] = winProb

		return json.dumps(response)

class Conf():
	def GET(self):
		form = web.input(conference=None, taper=None, date=None, season=2016, _unicode=False, division=None,
						 gender=None)
		setGenDiv(form.gender, form.division)

		start = Time.time()
		division = session.division
		gender = session.gender
		confList = conferences[division][gender]

		if form.conference is None:
			return render.conference(conferences=sorted(confList.keys()), scores=None, teamScores=None,
									 finalScores=None, table='', winTable=None)

		season = int(form.season)

		if form.date and form.date != 'Whole Season':  # parse the date string
			(month, day) = re.split('/', form.date)
			if month in ['10', '11', '12']:
				year = str(season - 1)
			else:
				year = str(season)
			swimdate = year + '-' + month + '-' + day
		else:
			swimdate = None

		if form.conference:
			if form.taper == 'Top Time':
				topTimes = True
			else:
				topTimes = False
			if form.conference == 'Nationals':
				confMeet = database.conference(teams=allTeams[gender][division], topTimes=topTimes, gender=gender,
											   season=season, divisions=division, date=swimdate)
				scores = confMeet.scoreString(25)
				teamScores = confMeet.scoreReport(repressSwim=True, repressTeam=True)
			else:
				confMeet = database.conference(teams=confList[form.conference], topTimes=topTimes, gender=gender,
											   season=season, divisions=division, date=swimdate)
				scores = confMeet.scoreString()
				teamScores = confMeet.scoreReport()
			print Time.time() - start
			winProb = confMeet.scoreMonteCarlo(runs=100)
		else:
			scores = None
			teamScores = None
			winProb = None
		if teamScores:
			table = googleTable(teamScores, scores['scores'])
		else:
			table = ''

		print Time.time() - start
		return render.conference(conferences=sorted(confList.keys()), scores=showMeet(scores),
								 teamScores=showTeamScores(teamScores), finalScores=showScores(scores),
								 table=table, winTable=showWinTable(winProb))

class ConfJSON():
	def GET(self):
		form = web.input(conference=None, taper=None, date=None, season=2016, division=None, gender=None)
		web.header("Content-Type", "application/json")
		division = form.division
		gender = form.gender
		confList = conferences[division][gender]

		if form.conference is None:
			return {}

		season = int(form.season)

		if form.date and form.date != 'Whole Season':  # parse the date string
			(month, day) = re.split('/', form.date)
			if month in ['10', '11', '12']:
				year = str(season - 1)
			else:
				year = str(season)
			swimdate = year + '-' + month + '-' + day
		else:
			swimdate = None

		if form.taper == 'Top Time':
			topTimes = True
		else:
			topTimes = False
		if form.conference == 'Nationals':
			confMeet = database.conference(teams=allTeams[gender][division], topTimes=topTimes, gender=gender,
										   season=season, divisions=division, date=swimdate)
			scores = confMeet.scoreString(25)
			teamScores = confMeet.scoreReport(repressSwim=True, repressTeam=True)
		else:
			confMeet = database.conference(teams=confList[form.conference], topTimes=topTimes, gender=gender,
										   season=season, divisions=division, date=swimdate)
			scores = confMeet.scoreString()
			teamScores = confMeet.scoreReport()
		winProb = confMeet.scoreMonteCarlo(runs=100)

		labeledScores = JSONScores(scores)

		response = {}
		response['individual results'] = labeledScores
		response['team scores'] = teamScores
		response['win probability'] = winProb

		return json.dumps(response)

class Times():
	def GET(self):
		division = session.division
		gender = session.gender
		confList = conferences[division][gender]
		form = web.input(conference=None, event=None, season=None, _unicode=False)
		scores = None
		if form.conference and form.event:
			season = form.season
			if form.conference == 'All':
				teams = []
				for conference in confList:
					for team in confList[conference]:
						teams.append(team)
			else:
				teams = confList[form.conference]
			if form.event == 'All':
				events = None
			else:
				events = [form.event]
			topTimes = database.topTimes(events=events, teams=teams, gender=gender, season=season)
			scores = showMeet(topTimes.scoreString(showNum=100, showScores=False, showPlace=True))

		return render.times(conferences=sorted(confList.keys()), events=eventOrder, scores=scores)

class Placing():
	def GET(self):
		division = session.division
		gender = session.gender
		form = web.input(_unicode=False)
		if len(form.keys()) == 0:  # initial load
			confTable = ''
		else:
			time = 0
			event = ''
			improvement = False
			for key in form.keys():
				if key == 'improvement':
					improvement = True
				else:
					try:
						if 'min' in key:
							time += 60*int(form[key])
						elif 'sec' in key:
							time += int(form[key])
						elif 'hun' in key:
							time += .01*int(form[key])
						elif 'event' in key:
							event = form[key]
					except ValueError:
						pass
			newSwims = set()
			if improvement:
				time *= 0.975
			newSwims.add((event, time))
			if len(newSwims) > 0:
				confPlaces = database.conferencePlace(division=division, gender=gender, newSwims=newSwims, year=2014)
				confTable = showConf(confPlaces, newSwims)
			else:
				confTable = ''

		return render.placing(conferences=confTable, events=eventOrder)

class Improvement():
	def GET(self):
		form = web.input(conference=None, season=None, gender=None, division=None)
		setGenDiv(form.gender, form.division)
		division = session.division
		gender = session.gender
		season = 2015
		confList = conferences[division][gender]

		if form.conference in confList:
			teams=confList[form.conference]
		elif form.conference == 'All':
			teams=allTeams[gender][division]
		else:
			return render.improvement(conferences=sorted(confList.keys()), table=None)

		if form.season in {'2016', '2015', '2014', '2013'}:
			season1 = int(form.season)
			season2 = int(form.season) - 1
			teamImp = database.getImprovement(gender=gender, season1=season1, season2=season2, teams=teams)
			table = googleCandle(teamImp)
		elif form.season == 'All':
			season1 = season
			season2 = season - 3
			teamImp = database.getImprovement(gender=gender, season1=season1, season2=season2, teams=teams)
			table = googleCandle(teamImp)
		else:
			table = None

		return render.improvement(conferences=sorted(confList.keys()), table=table)

class ImprovementJSON():
	def GET(self):
		form = web.input(conference=None, season=None, gender=None, division=None)
		web.header("Content-Type", "application/json")
		division = form.division
		gender = form.gender
		season = 2015
		confList = conferences[division][gender]

		if form.conference in confList:
			teams = confList[form.conference]
		elif form.conference == 'All':
			teams = allTeams[gender][division]
		else:
			return []

		if form.season in {'2016', '2015', '2014', '2013'}:
			season1 = int(form.season)
			season2 = int(form.season) - 1
			teamImp = database.getImprovement(gender=gender, season1=season1, season2=season2, teams=teams)
		elif form.season == 'All':
			season1 = season
			season2 = season - 3
			teamImp = database.getImprovement(gender=gender, season1=season1, season2=season2, teams=teams)
		else:
			teamImp = None

		jsonImp = {}
		for team in teamImp:
			if teamImp[team] == []:
				continue
			jsonImp[team] = {}
			med = numpy.median(teamImp[team])
			nums = teamImp[team]
			jsonImp[team]['min'] = min(nums)
			jsonImp[team]['bottomquartile'] = numpy.percentile(nums, 25)
			jsonImp[team]['topquartile'] = numpy.percentile(nums, 75)
			jsonImp[team]['max'] = max(nums)
			jsonImp[team]['median'] = med
			jsonImp[team]['n'] = len(nums)

		return json.dumps(jsonImp)

class Rankings():
	def GET(self):
		form = web.input(conference=None, season=None, gender=None, division=None, dual=None)
		setGenDiv(form.gender, form.division)
		division = session.division
		gender = session.gender
		confList = conferences[division][gender]

		if form.dual == 'Dual':
			invite = False
		else:
			invite = True
		if form.season in {'2017', '2016', '2015', '2014', '2013', '2012'}:
			seasons = {int(form.season)}
			bar = True
		else:
			seasons = {2017, 2016, 2015, 2014, 2013, 2012}
			bar = False
		scores = {}
		if not form.conference or not (form.conference in confList):
			return render.rankings(conferences=sorted(confList.keys()), table=None, bar=False)
		teams = confList[form.conference]

		for team in teams:
			scores[team] = {}
			for season in seasons:
				try:
					teamseason = TeamSeason.get(team=team, gender=gender, season=season, division=division)
					strength = teamseason.getStrength(invite=invite)
					if strength > 0:
						scores[team][season] = strength
				except TeamSeason.DoesNotExist:
					pass
		if bar:
			table = googleBar(scores)
		else:
			table = googleLine(scores)
		return render.rankings(conferences=sorted(confList.keys()), table=table, bar=bar)

class Programs():
	def GET(self):
		form = web.input(conference=None, tableOnly=False, gender=None, division=None)

		setGenDiv(form.gender, form.division)

		division = session.division
		gender = session.gender
		allConfs = conferences[division][gender]

		if (not form.conference or not form.conference in allConfs) and form.conference != 'All':
			return render.programs(conferences=sorted(allConfs.keys()), rankings=None)
		teamRecruits = {}
		teamImprovement = {}
		teamAttrition = {}

		if form.conference != 'All':
			confs = [form.conference]
		else:
			confs = allConfs

		for conference in confs:
			for team in conferences[division][gender][conference]:
				for stats in Team.select(Team.strengthinvite, Team.attrition, Team.improvement).where(Team.name==team,
															Team.gender==gender, Team.division==division):

					teamRecruits[team] = stats.strengthinvite
					teamAttrition[team] = stats.attrition
					teamImprovement[team] = stats.improvement

		teamRank = {}
		for i, dict in enumerate([teamRecruits, teamAttrition, teamImprovement]):
			for idx, teamScore in enumerate(sorted(dict.items(), key=itemgetter(1), reverse=True), start=1):
				(team, score) = teamScore
				if not team in teamRank:
					teamRank[team] = []
					teamRank[team].append(0)
				teamRank[team][0] += idx
				teamRank[team].append((idx, score))

		html = showPrograms(teamRank)
		return render.programs(conferences=sorted(allConfs.keys()), rankings=html)

class ProgramsJSON():
	def GET(self):
		form = web.input(conference=None, tableOnly=False, gender=None, division=None)
		web.header("Content-Type", "application/json")
		division = session.division
		gender = session.gender
		allConfs = conferences[division][gender]

		if (not form.conference or not form.conference in allConfs) and form.conference != 'All':
			return json.dumps({})
		teamRecruits = {}
		teamImprovement = {}
		teamAttrition = {}

		if form.conference != 'All':
			confs = [form.conference]
		else:
			confs = allConfs

		for conference in confs:
			for team in conferences[division][gender][conference]:
				for stats in Team.select(Team.strengthinvite, Team.attrition, Team.improvement).where(Team.name==team,
															Team.gender==gender, Team.division==division):

					teamRecruits[team] = stats.strengthinvite
					teamAttrition[team] = stats.attrition
					teamImprovement[team] = stats.improvement

		teamRank = {}
		for i, dict in enumerate([teamRecruits, teamAttrition, teamImprovement]):
			for idx, teamScore in enumerate(sorted(dict.items(), key=itemgetter(1), reverse=True), start=1):
				(team, score) = teamScore
				if not team in teamRank:
					teamRank[team] = []
					teamRank[team].append(0)
				teamRank[team][0] += idx
				teamRank[team].append((idx, score))

		teamRankLabel = {}
		for team in teamRank:
			teamRankLabel[team] = {}
			teamRankLabel[team]['totalscore'] = teamRank[team][0]
			for (idx, part) in enumerate(teamRank[team][1:]):
				if idx == 0:
					teamRankLabel[team]['strength'] = {'rank': part[0], 'value': part[1]}
				elif idx == 1:
					teamRankLabel[team]['attrition'] = {'rank': part[0], 'value': part[1]}
				elif idx == 2:
					teamRankLabel[team]['improvement'] = {'rank': part[0], 'value': part[1]}

		return json.dumps(teamRankLabel)

class SeasonRankings():
	def GET(self):
		form = web.input(gender=None, division=None)
		setGenDiv(form.gender, form.division)

		oldTopTeams = database.teamRank(gender=session.gender, division=session.division, season=2017)

		rank = showRank(oldTopTeams)
		return render.preseason(rank)

class TeamStats():
	def GET(self, team=None):
		form = web.input(gender=None, division=None, season=2017)
		season = form.season
		team = str.replace(str(team), '+', ' ')  # modify back to spaces in URL
		setGenDiv(form.gender, form.division)
		if not team:
			return render.teamstats(None, None, None, None, None, None, None, None, None)

		try:
			teamseason = TeamSeason.get(TeamSeason.team==team, TeamSeason.division==session.division,
										TeamSeason.season==season, TeamSeason.gender==session.gender)
		except TeamSeason.DoesNotExist:
			return render.teamstats(None, None, None, None, None, None, None, None, None)

		# team speed
		# dual strength, invite strength, nats%, conf%
		#print teamseason.season
		winNats = round(teamseason.getWinnats(), 3) * 100
		winConf = round(teamseason.getWinconf(), 3) * 100

		# team development
		# print team, session.gender, session.division
		try:
			stats = Team.get(Team.name==team, Team.gender==session.gender, Team.division==session.division)
			inviteStr = stats.strengthinvite
			attrition = round(stats.attrition, 3)
			imp = round(stats.improvement, 3)
		except Team.DoesNotExist:
			inviteStr = None
			attrition = None
			imp = None
		inviteStr = teamseason.getStrength()

		# top swimmers
		topSwimmers = teamseason.getTopSwimmers(17)
		#print topSwimmers
		swimTable = showTopSwimmers(topSwimmers)

		if teamseason.getTaperStats():
			(medtaper, stdtaper) = teamseason.getTaperStats()
		else:
			(medtaper, stdtaper) = 0, 0
		#print medtaper, stdtaper

		conf = teamseason.conference
		return render.teamstats(team, inviteStr, attrition, imp, winConf, winNats, swimTable, conf, medtaper)

class teamMeets():
	def GET(self):
		form = web.input(team=None, division=None, season=None)
		web.header("Content-Type", "application/json")

		if form.division:
			division = form.division.strip()
		else:
			return
		if form.team in meetList[session.gender][division]:
			seasonMeets = meetList[session.gender][division][form.team]
			if form.season and int(form.season) in seasonMeets:
				meets = seasonMeets[int(form.season)]
				return json.dumps(meets)

			# on first load, default season
			return json.dumps(seasonMeets)
		else:
			return json.dumps()

	def POST(self):
		form = web.input(team=None, division=None, season=None)
		web.header("Content-Type", "application/json")

		if form.division:
			division = form.division.strip()
		else:
			return
		if form.team in meetList[session.gender][division]:
			seasonMeets = meetList[session.gender][division][form.team]
			if form.season and int(form.season) in seasonMeets:
				meets = seasonMeets[int(form.season)]
				'''
				meetScores = []
				for meet in seasonMeets[int(form.season)]:
					score = sqlmeets.Meet(meet, teams=form.team, season=form.season).expectedScores(
						division=form.division)[
						form.team]
					meetScores.append([meet, score])
				meets = []
				for meet, score in sorted(meetScores, key=lambda score: score[1]):
					meets.append(meet + ": " + str(score))
				'''
				return json.dumps(meets)

			# on first load, default season
			return json.dumps(seasonMeets)
		else:
			return

class getConfs():
	def GET(self):
		form = web.input(division=None, gender=None)
		web.header("Content-Type", "application/json")
		try:
			return json.dumps(conferences[form.division][form.gender].keys())
		except:
			return json.dumps()

class getTeams():
	def GET(self):
		form = web.input(division=None, gender=None)
		web.header("Content-Type", "application/json")
		try:
			return json.dumps(allTeams[form.gender][form.division])
		except:
			return json.dumps()

# HTML generators

def showMeet(scores):
	if scores == None: return None
	html='<h2 align="center">Simulated Results</h2>'
	html+='<table>'
	for event in eventOrder:
		if not event in scores: continue
		html += '<tr><th align="left" colspan=6>' + event + '</th></tr>'
		for swim in scores[event]:
			html += '<tr>'
			for part in swim:
				html += '<td>'+str(part)+'</td>'
			html += '</tr>'
	html += '</table></br>'
	return html

def showScores(scores):
	if scores == None: return None
	html ='<h2 align="center">	Final Scores </h2>'
	html += '<table>'
	for swim in scores['scores']:
		html += '<tr>'
		for part in swim:
			html += '<td>'+str(part)+'</td>'
		html += '</tr>'
	html += '</table>'
	return html
	
def showTeamScores(teamScores, showType='swimmer'):
	#type = swimmer,event, or year
	if teamScores == None: return None
	html = '<h2 align="center">	Score Report </h2>'
	html += '<form>'
	html += 'Show By: <select type="text" onchange="sumType(this.form);" id="summaryType">'
	html += '<option>swimmer</option> <option>event</option> <option>year</option>'
	html += '</select>'
	html += '</form>'
	teams = {team: teamScores[team]['total'] for team in teamScores}
	for type in ['swimmer', 'event', 'year']:
		if type==showType: html += '<table id="' + type + '">'
		else: html += '<table class="hidden" id="' + type + '">'
		for team in sorted(teams, key=teams.__getitem__, reverse=True):
			html += '<tr> <th>'+team+'</th> </tr>'
			if not type in teamScores[team]: continue
			for name in sorted(teamScores[team][type], key=teamScores[team][type].__getitem__, reverse=True):
				html += '<tr>'
				html += '<td>'+name+'</td> <td>'+str(teamScores[team][type][name])+'</td>'
				html += '</tr>'
		html += '</table>'
	return html

def showConf(scores, newSwims):
	html = ''
	for conference in sorted(scores.keys()):
		html += '<div id="container">'
		html += '<table class="conf">'
		html += '<tr><th>'
		html += conference
		html += '</th></tr>'
		for swim in newSwims:
			event = swim[0]
			html += '<tr><td>'
			html += event + ': ' + '<b>' + str(scores[conference][event]) + '<b>'
			html += '</td><tr>'
		html += '</table>'
		html += '</div>'

	return html

def showPrograms(teamRank):
	html = ''
	html += '<table id="programs">'
	html += '<thead><tr>'
	html += '<th>Rank</th>'
	html += '<th>Team</th>'
	html += '<th>Combined Score</th>'
	html += '<th>Strength Rank</th>'
	html += '<th>Team Strength</th>'
	html += '<th>Attrition Rank</th>'
	html += '<th>Attrition Rate</th>'
	html += '<th>Improvement Rank</th>'
	html += '<th>Improvement %</th>'
	html += '</tr></thead>'
	html += '<tbody>'
	for (teamRank, teamStats) in enumerate(sorted(teamRank.items(), key=itemgetter(1))):
		#('Carleton', [6, (3, -113), (1, 0.08433734939759036), (2, -0.60857689914529911)])
		(team, rank) = teamStats
		html += '<tr>'
		html += '<td>' + str(teamRank+1) + '</td>'
		html += '<td>' + team + '</td>'
		html += '<td>' + str(rank[0]) + '</td>'
		for (idx, part) in enumerate(rank[1:]):
			html += '<td>' + str(part[0]) + '</td>'
			html += '<td>' + str(round(part[1], 3)) + '</td>'
		html += '<tr>'

	html += '</tbody>'
	html += '</table>'

	return html

def showTopRanking(topTeams):
	html = ''
	html += '<table id="topteams">'
	html += '<thead><tr>'
	html += '<th>Rank</th>'
	html += '<th>Team</th>'
	html += '<th>National Win %</th>'
	html += '<th>Conference</th>'
	html += '<th>Conference Win %</th>'
	html += '<th>Power Invite</th>'
	html += '<th>Power Dual</th>'
	html += '</tr></thead>'
	html += '<tbody>'
	for idx, team in enumerate(topTeams):
		html += '<tr>'
		html += '<td>' + str(idx+1) + '</td>'
		html += '<td>' + team.team + '</td>'
		html += '<td class=percent>' + str(team.winnats * 100) + '</td>'
		html += '<td>' + team.conference + '</td>'
		html += '<td class=percent>' + str(team.winconf * 100) + '</td>'
		html += '<td class=invpow>' + str(team.strengthinvite) + '</td>'
		html += '<td class=dualpow>' + str(team.strengthdual) + '</td>'
		html += '<tr>'

	html += '</tbody>'
	html += '</table>'

	return html

def showRank(topTeams):
	html = ''
	html += '<table id="topteams">'
	html += '<thead><tr>'
	html += '<th>Rank</th>'
	html += '<th>Team</th>'
	html += '<th>National Win % (delta)</th>'
	html += '<th>Conference</th>'
	html += '<th>Conference Win % (delta)</th>'
	html += '<th>Invite Strength</th>'
	html += '<th>Dual Strength</th>'
	html += '</tr></thead>'
	html += '<tbody>'
	for idx, team in enumerate(topTeams):
		html += '<tr>'
		html += '<td>' + str(idx+1) + '</td>'
		html += '<td> <a href=/teamstats/' + str.replace(str(team.team), ' ', '+') + '>' + team.team + '</a></td>'
		winNats = team.getWinnats() * 100
		if winNats == '': winNatsDelta = ''
		else: winNatsDelta = winNats - team.getWinnats(1) * 100
		winConf = team.getWinconf() * 100
		if winConf == '': winConfDelta = ''
		else: winConfDelta = winConf - team.getWinconf(1) * 100

		if winNatsDelta > 0:
			natsColor = 'green'
		elif winNatsDelta < 0:
			natsColor = 'red'
		else:
			natsColor = 'gray'
		if winConfDelta > 0:
			confColor = 'green'
		elif winConfDelta < 0:
			confColor = 'red'
		else:
			confColor = 'gray'

		html += '<td class=percent>' + str(winNats)\
				+'<span style="color:' + natsColor + ';"> (' + str(winNatsDelta) + ')</span></td>'
		# html += '<td class=percent>' + str(winNats) + '</td>'
		html += '<td>' + team.conference + '</td>'
		# html += '<td class=percent>' + str(winConf) + '</td>'
		if team.conference:
			html += '<td class=percent>' + str(winConf)\
				+'<span style="color:' + confColor + ';"> (' + str(winConfDelta) + ')</span></td>'
		else:
			html += '<td class=percent></td>'
		html += '<td class=invpow>' + str(team.getStrength()) + '</td>'
		html += '<td class=dualpow>' + str(team.getStrength(invite=False)) + '</td>'
		html += '<tr>'

	html += '</tbody>'
	html += '</table>'

	return html

def showTopSwimmers(swimmers):
	html = ''
	html += '<table id="topswimmers">'
	html += '<thead><tr>'
	html += '<th>Rank</th>'
	html += '<th>Name</th>'
	html += '<th>Year</th>'
	html += '<th>Power Score</th>'
	html += '<th>Top Events</th>'
	html += '</tr></thead>'
	html += '<tbody>'
	for (idx, (score, swimmer)) in enumerate(swimmers):
		html += '<tr>'
		html += '<td>' + str(idx + 1) + '</td>'
		html += '<td>' + swimmer.name + '</td>'
		html += '<td>' + swimmer.year + '</td>'
		html += '<td>' + str(int(score)) + '</td>'
		topSwims = swimmer.getTaperSwims()
		swimStr =''
		for event in topSwims:
			#print topSwims[event].getPPTs()
			#print int(topSwims[event].getPPTs())
			#print str(int(topSwims[event].getPPTs()))
			swimStr += event + ': <b>' + swimTime(topSwims[event].time)\
					   + ' (' + str(int(topSwims[event].getPPTs())) + ')</b> - '
		html += '<td>' + swimStr + '</td>'
		html += '<tr>'

	html += '</tbody>'
	html += '</table>'
	return html

def googleTable(teamScores, scores):
	table = ["['Name','Parent','Score'],"]
	table.append("['All Teams', null, 0],")
	for score in scores:
		if score[1] == 0: continue
		team = score[0]
		team = re.sub("'", "", team)
		table.append("['" + team + "','All Teams' ," + str(score[1]) + "],")
	for team in teamScores:
		for swimmer in teamScores[team]['swimmer']:
			if swimmer == 'Relays': continue
			score = teamScores[team]['swimmer'][swimmer]
			swimmerName = re.sub("'", "", swimmer)
			if score == 0: continue
			teamName = re.sub("'", "", team)
			table.append("['" + swimmerName + "','" + teamName + "'," + str(score) + "],")
	return table

def googleCandle(confImp):
	table = []
	teamord = []
	for team in confImp:
		if confImp[team] == []: continue
		teamord.append((team, numpy.median(confImp[team])))
	for team, med in sorted(teamord, key=lambda score: score[1], reverse=True):
		nums = confImp[team]
		teamName = re.sub("'", "", team)
		table.append("['" + teamName + "'," + str(min(nums))+","+str(numpy.percentile(nums, 25))+","+str(numpy.percentile(
			nums, 75))+","+str(max(nums)) + ",'" + str(round(med, 2)) + ' n=' + str(len(nums)) + "'],")
	return table

def googleLine(teams):
	table = []
	line = "['Season'"
	for team in teams:
		teamName = re.sub("'", "", team)
		line += ",'{}'".format(teamName)
	line += "],"
	table.append(line)

	for team in teams:
		seasons = teams[team].keys()
		break
	seasons.sort()
	for season in seasons:
		line = "['{0}'".format(season)
		for team in teams:
			if season in teams[team]:
				score = teams[team][season]
			else:
				score = 0
			if score == None:
				score = 0
			line += ",{0}".format(score)
		line += "],"
		table.append(line)
	return table

def googleBar(teamsOld):
	table = ["['Team', 'Score'],"]
	teams = []
	for team in teamsOld:
		for season in teamsOld[team]:  # should only be one
			teams.append((team, teamsOld[team][season]))

	for team, score in sorted(teams, key=lambda score: score[1]):
		teamName = re.sub("'", "", team)
		line = "['{0}',{1}],".format(teamName, score)
		table.append(line)
	return table

def googleJSON(teams):
	description = {"season": ("string", "Season")}
	for team in teams:
		description[team] = ("string", team)

	for team in teams:
		seasons = teams[team].keys()
		break

	data = []
	for season in seasons:
		line = {'season': season}
		for team in teams:
			line[team] = teams[team][season]
		data.append(line)

# generate html for winProb table
def showWinTable(winProb, top=20):
	# average placing for sorting
	avgTeamPlace = {}
	for team in winProb:
		avgPlace = 0
		for (i, prob) in enumerate(winProb[team]):
			avgPlace += (i+1) * prob
		avgTeamPlace[team] = avgPlace
	html = '<div id="winProbs">'
	html += '<table><tr>'
	html += '<th></th>'
	# placing header
	for i in range(1, len(winProb)+1):
		if i > top + 1: break  # one for name column
		html += '<th>'
		html += str(i)
		html += '</th>'
	html += '</tr>'
	for (team, place) in sorted(avgTeamPlace.items(), key=itemgetter(1)):  # sort by average place
		if place > top: break  # only top so many teams
		html += '<tr>'
		html += '<td>' + team + '</td>'
		for (idx, prob) in enumerate(winProb[team]):
			if idx > top: break
			html += '<td>'
			html += str(prob*100) + '%'
			html += '</td>'
		html += '</tr>'
	html += '</table>'
	html += '</div>'

	return html

def JSONScores(scores):
	# label scoring
	scoresLabel = {}
	for event in scores:
		scoresLabel[event] = {}
		for swimmer in scores[event]:
			#print swimmer
			if len(swimmer) == 5:
				(name, team, event, time, score) = swimmer
				meet = None
			elif len(swimmer) == 4:
				(name, team, event, time) = swimmer
				score = 0
				meet = None
			elif len(swimmer) == 6:
				(name, team, event, time, meet, score) = swimmer
			else:
				print swimmer
				continue
			scoresLabel[event][name] = {}
			scoresLabel[event][name] = {'team': team, 'time': time, 'score': score, 'meet': meet}
	return scoresLabel

if __name__ == "__main__":
	app.run()
