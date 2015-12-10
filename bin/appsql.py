import web
import sqlmeets
import operator
import re
import json
import os, urlparse
import numpy
from peewee import *
from datetime import date

eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay"]
eventOrderInd = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley"]

urls = ('/', 'Home',
	'/home', 'Home',
	'/swimulate', 'Swim',
	'/fantasy', 'Fantasy',
	'/conference', 'Conf',
	'/times', 'Times',
	'/duals', 'Duals',
	'/placing', 'Placing',
	'/improvement', 'Improvement',
	'/rankings', 'Rankings',
	'/teamMeets', 'teamMeets'
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

def getConfs(confFile):
	with open(confFile, 'r') as file:
		confs = {'D1': {}, 'D2': {}, 'D3': {}}
		for line in file:
			parts = re.split('\t', line.strip())
			division = parts[0]
			conf = parts[1]
			team = parts[2]
			if not conf in confs[division]:
				confs[division][conf] = set()
			confs[division][conf].add(team)
	return confs

def clean(meetList):
	newList = {}
	for team in meetList:
		newList[team] = {}
		for season in meetList[team]:
			newList[team][season] = []
			for meet in meetList[team][season]:
				newList[team][season].append(re.sub('\"', '\\\\\"', meet))
	return newList

web.config.debug = False
app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'gender': 'Women', 'division':
	'D3','season': 2016})
render = web.template.render('templates/', base="layout", globals={'context': session})

app.add_processor(connection_processor)

database = sqlmeets.SwimDatabase(database=db)
meetList = clean(database.teamMeets)
conferences = getConfs('data/conferences.txt')

allTeams = {}
for division in conferences:
	allTeams[division] = []
	for conference in conferences[division]:
		for team in conferences[division][conference]:
			allTeams[division].append(team)
for division in allTeams:
	allTeams[division].sort()

class Home():
	def GET(self):
		return render.home()

	def POST(self):
		form = web.input(gender=session.gender, division=session.division, season=session.season, _unicode=False)
		session.gender = form.gender
		session.division = form.division
		session.season = int(form.season)

		web.header("Content-Type", "application/json")
		return 'an error'

class Swim(object):
	def GET(self):
		gender = session.gender

		form = web.input(team1=None, team2=None, meet1=None, meet2=None, _unicode=False)
		keys = form.keys()
		
		formMeets = {}
		for key in keys:
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
			return render.swimulator(divTeams=allTeams, scores=None, teamScores=None, finalScores=None)
		
		else:
			newMeet = database.swimMeet(formMeets.values(), gender=gender, includeEvents=sqlmeets.requiredEvents,
										selectEvents=False,
										resetTimes=True)
			if optimizeTeams:
				newMeet = database.lineup(optimizeTeams, newMeet, gender=gender)
			if len(formMeets) > 2:
				showNum = 20
			else:
				showNum = 6	
			scores = newMeet.scoreString(showNum=showNum)
			teamScores = newMeet.scoreReport(printout=False)
			newMeet.reset(True, True)

			return render.swimulator(divTeams=allTeams, scores=showMeet(scores), teamScores=showTeamScores(
				teamScores), finalScores=showScores(scores))

class Fantasy(object):
	def GET(self):
		return render.fantasy()
		
class Conf(object):
	def GET(self):
		division = session.division
		gender = session.gender
		season = session.season
		confList = conferences[division]
		form = web.input(conference=None, taper=None, date=None, _unicode=False)
		if form.date and form.date != 'Whole Season':
			(month, day) = re.split('/', form.date)
			if month in ['10', '11', '12']:
				year = str(season - 1)
			else:
				year = str(season)
			swimdate = year + '-' + month + '-' + day
		else:
			swimdate = None
		print swimdate
		if form.conference:
			if form.taper == 'Top Time':
				topTimes = True
			else:
				topTimes = False
			if form.conference == 'Nationals':
				confMeet = database.conference(teams=allTeams[division], topTimes=topTimes, gender=gender,
											   season=season, divisions=division)
				scores = confMeet.scoreString(25)
				teamScores = confMeet.scoreReport(printout=False, repressSwim=True, repressTeam=True)
			else:
				confMeet = database.conference(teams=confList[form.conference], topTimes=topTimes, gender=gender,
											   season=season, divisions=division, date=swimdate)
				scores = confMeet.scoreString()
				teamScores = confMeet.scoreReport(printout=False)
		else:
			scores = None
			teamScores = None
		if teamScores:
			table = googleTable(teamScores, scores['scores'])
		else:
			table = ''
		return render.conference(conferences=sorted(confList.keys()), scores=showMeet(scores), teamScores=showTeamScores(teamScores), finalScores=showScores(scores), table=table)

class Times(object):
	def GET(self):
		division = session.division
		gender = session.gender
		season = session.season
		confList = conferences[division]
		form = web.input(conference=None, event=None, _unicode=False)
		scores = None
		if form.conference and form.event:
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

class Duals(object):
	def GET(self):
		division = session.division
		gender = session.gender
		season = session.season
		confList = conferences[division]
		
		form = web.input(conference=None)
		confName = form.conference
		
		if confName:
			if confName == 'All Teams':
				teams = allTeams[division]
			else:
				teams = confList[confName]
			topDuals = database.topDual(teams=teams, gender=gender, season=season)
			
			wins = topDuals[1]
			losses = topDuals[2]
			teams = sorted(wins.items(), key=operator.itemgetter(1), reverse=True)
			meets = topDuals[0]
			for team in meets:
				meets[team] = str(meets[team])
		else:
			wins = None
			losses = None
			teams = None
			meets = None
		
		return render.duals(wins=wins, losses=losses, teams=teams, meet=meets, conferences=sorted(confList.keys()))

class Placing(object):
	def GET(self):
		division = session.division
		gender = session.gender
		season = session.season
		form = web.input(_unicode=False)
		if len(form.keys()) == 0:  # initial load
			confTable = ''
		else:
			times = [0, 0, 0]
			events = ['', '', '']
			improvement = False
			for key in form.keys():
				if key == 'improvement':
					improvement = True
				else:
					num = int(key[-1]) - 1
					try:
						if 'min' in key:
							times[num] += 60*int(form[key])
						elif 'sec' in key:
							times[num] += int(form[key])
						elif 'hun' in key:
							times[num] += .01*int(form[key])
						elif 'event' in key:
							events[num] = form[key]
					except ValueError:
						pass
			newSwims = set()
			for i in range(len(events)):
				if times[i] == 0:  # remove nonexistant swims
					continue
				elif improvement:
					times[i] *= 0.975
				newSwims.add((events[i], times[i]))
			if len(newSwims) > 0:
				confPlaces = database.conferencePlace(division=division, gender=gender, newSwims=newSwims)
				confTable = showConf(confPlaces, newSwims)
			else:
				confTable = ''

		return render.placing(conferences=confTable, events=eventOrder)

class Improvement():
	def GET(self):
		division = session.division
		gender = session.gender
		#season = session.season - 1
		season = 2016
		confList = conferences[division]
		form = web.input(conference=None, season=None)

		if form.conference in confList:
			teams=confList[form.conference]
		elif form.conference == 'All':
			teams=allTeams[division]
		else:
			return render.improvement(conferences=sorted(confList.keys()), table=None)

		if form.season in {'2016', '2015', '2014', '2013'}:
			season1 = int(form.season)
			season2 = int(form.season) - 1
			season3 = None
			season4 = None
			teamImp, indImp = database.improvement(gender=gender, season1=season1, season2=season2,
												   season3=season3, season4=season4, teams=teams)
			table = googleCandle(teamImp)
		elif form.season == 'All':
			season1 = season
			season2 = season - 1
			season3 = season - 2
			season4 = season - 3
			teamImp, indImp = database.improvement(gender=gender, season1=season1, season2=season2,
												   season3=season3, season4=season4, teams=teams)
			table = googleCandle(teamImp)
		elif form.season == 'High School':
			teamImp, indImp = database.HSImprovement(gender=gender, teams=teams)

			#print indImp, teamImp
			table =googleCandle(teamImp)
		else:
			table = None

		return render.improvement(conferences=sorted(confList.keys()), table=table)

class Rankings():
	def GET(self):
		confList = conferences[session.division]
		form = web.input(conference=None, dual=None, season=None)

		recruits = False
		if form.dual == 'Dual':
			dual = True
		else:
			dual = False
		if form.season in {'2016', '2015', '2014', '2013', '2012'}:
			seasons = {int(form.season)}
			bar = True
		elif form.season == 'Recruits':
			seasons = {'All Recruits'}
			recruits = True
			bar = True
		else:
			seasons = {2015, 2014, 2013, 2012}
			bar = False
		scores = {}
		if form.conference in confList:
			teams = confList[form.conference]
		elif form.conference == 'All':
			teams = allTeams[session.division]
		else:
			return render.rankings(conferences=sorted(confList.keys()), table=None, bar=False)

		#print form.season, recruits
		for team in teams:
			scores[team] = {}
			for season in seasons:
				scores[team][season] = database.topTeamScore(team=team, dual=dual, season=season,
															  gender=session.gender, division=session.division,
															  recruits=recruits)
		# remove nulls
		remove = set()
		for team in scores:
			remove.add(team)
			for season in scores[team]:
				if scores[team][season]:
					remove.remove(team)
					break
		for team in remove:
			del scores[team]


		if bar:
			table = googleBar(scores)
		else:
			table = googleLine(scores)
		return render.rankings(conferences=sorted(confList.keys()), table=table, bar=bar)

class teamMeets():
	def POST(self):
		form = web.input(team=None, season=None, division=None)
		web.header("Content-Type", "application/json")
		if form.team in meetList:
			seasonMeets = meetList[form.team]
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
				return json.dumps(meets)  # seasonMeets[int(form.season)])

			#on first load, default season
			return json.dumps(seasonMeets)
		else:
			return


#HTML generators

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
	for season in seasons:
		line = "['{0}'".format(season)
		for team in teams:
			score = teams[team][season]
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


if __name__ == "__main__":
	app.run()