import web
import meets
import operator
import re

eventOrder=["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","1 mtr Diving","3 mtr Diving"]

urls = ('/', 'Home',
	'/swimulate', 'Swim',
	'/fantasy', 'Fantasy',
	'/conference', 'Conf',
	'/times', 'Times',
	'/duals', 'Duals',
)

web.config.debug = False
meets.start(file='./bin/D3_15_12-12', gender='Men')
databaseMenD3 = meets.database

meets.start(file='./bin/D3_15_12-12', gender='Women')
databaseWomenD3 = meets.database

meets.start(file='./bin/D2_15_12-15', gender='Men')
databaseMenD2 = meets.database

meets.start(file='./bin/D2_15_12-15', gender='Women')
databaseWomenD2 = meets.database

meets.start(file='./bin/D1_15_12-12', gender='Men')
databaseMenD1 = meets.database

meets.start(file='./bin/D1_15_12-12', gender='Women')
databaseWomenD1 = meets.database

topDuals = {'men': {'D1': {}, 'D2': {}, 'D3': {}}, 'women': {'D1': {}, 'D2': {}, 'D3': {}}}
gender = 'men'
division = 'D3'

app = web.application(urls, globals())
render = web.template.render('templates/', base="layout")

def getTeamMeets(database):
	teamMeets = {}
	for team in database.teams:
		teamMeets[team]=[]
		for season in database.teams[team].meets:
			for meet in database.teams[team].meets[season]:
				meet = re.sub('\"','\\\\\"',meet)
				teamMeets[team].append(meet)
	return teamMeets

def getConfList(database):
	conferences = database.conferences
	confList = conferences.keys()
	confList.sort()
	return confList

def getDatabase():
	if gender == 'women':
		if division == 'D1':
			database = databaseWomenD1
		elif division == 'D2':
			database = databaseWomenD2
		else:
			database = databaseWomenD3
	else:
		if division == 'D1':
			database = databaseMenD1
		elif division == 'D2':
			database = databaseMenD2
		else:
			database = databaseMenD3
	return database

class Home():
	def GET(self):
		form = web.input(gender=None,division=None)
		global gender,division
		if form.gender and form.gender != gender:
			gender = form.gender
		if form.division and form.division != division:
			division = form.division
		return render.home(gender,division)

class Swim(object):
	def GET(self):
		database = getDatabase()
		teamMeets = getTeamMeets(database)
		confList = getConfList(database)
		
		form = web.input(team1=None,team2=None,meet1=None,meet2=None)
		keys = form.keys()
		
		teamsMeets = {}
		createLineup = False
		exit = False
		for key in keys:
			num = int(key[-1])
			if not num in teamsMeets:
				teamsMeets[num]=[None,None]
			if "team" in key:
				teamsMeets[num][0]=form[key]
			elif "meet" in key:
				if form[key]=='Create Lineup': #can't have two or more create lineups
					if createLineup:
						exit = True
					else:
						createLinup = True
					teamsMeets[num][1]='Create Lineup'
				elif form[key]:
					teamsMeets[num][1]=database.meets[form[key]]
		
		if exit: return render.swimulator(teamMeets,scores=None,teamScores=None,finalScores=None)	
		
		#use topDual if no meet?
		remove=set()
		optimizeTeam = None
		for num in teamsMeets:
			tm = teamsMeets[num]
			if not tm[0] or not tm[1]:
				remove.add(num)
			elif tm[1] == 'Create Lineup':
				optimizeTeam = tm[0]
				remove.add(num)
		for tm in remove:
			del(teamsMeets[tm])
		
		if len(teamsMeets) < 1: return render.swimulator(teamMeets,scores=None,teamScores=None,finalScores=None)
		
		else:
			newMeet = database.swimMeet(teamsMeets.values(),includeEvents=meets.requiredEvents,selectEvents=True,resetTimes=True)			
			if optimizeTeam:
				newMeet = database.lineup(optimizeTeam,newMeet)
			if len(teamsMeets) > 2:
				showNum = 20
			else:
				showNum = 6	
			scores = newMeet.scoreString(showNum=showNum)
			teamScores = newMeet.scoreReport(printout=False)
				
			return render.swimulator(teamMeets = teamMeets,scores = showMeet(scores),teamScores=showTeamScores(teamScores),finalScores=showScores(scores))

class Fantasy(object):
	def GET(self):
		return render.fantasy()
		
class Conf(object):
	def GET(self):
		database = getDatabase()
			
		teamMeets = getTeamMeets(database)
		confList = getConfList(database)
		
		form = web.input(conference=None, taper=None)
		if form.conference:
			if form.taper == 'Top Time':
				topTimes=True
			else:
				topTimes=False
			if form.conference == 'Nationals':
				confMeet = database.conference(teams=database.teams.keys(), topTimes=topTimes)
				scores = confMeet.scoreString(25)
				teamScores = confMeet.scoreReport(printout=False, repressSwim=True, repressTeam=True)
			else:
				print form.conference
				conf = database.conferences[form.conference]
				confMeet = database.conference(teams=conf.teams, topTimes=topTimes)
				scores = confMeet.scoreString()
				teamScores = confMeet.scoreReport(printout=False)
		else:
			scores = None
			teamScores = None
		return render.conference(conferences=confList, scores=showMeet(scores), teamScores=showTeamScores(teamScores), finalScores=showScores(scores))
		
		
class Times(object):
	def GET(self):
		database = getDatabase()
		confList = getConfList(database)
		form = web.input(conference=None,event=None)
		scores = None
		if form.conference and form.event:
			if form.conference in database.conferences:
				teams = database.conferences[form.conference].teams
			else:
				teams = 'all'
			if form.event == 'All':
				events = 'all'
			else:
				events = {form.event}
			topTimes = database.topTimesReport(events=events, teams=teams)
			scores = showMeet(topTimes.scoreString(showNum=100, showScores=False, showPlace=True))

		return render.times(conferences=confList, events=eventOrder, scores=scores)


class Duals(object):
	def GET(self):
		database = getDatabase()
		confList = getConfList(database)
		
		form = web.input(conference=None)
		confName = form.conference
		
		if confName:
			#cache
			global topDuals
			if not confName in topDuals[gender][division]:
				if confName in database.conferences:
					teams = database.conferences[confName].teams
				else:
					teams = 'all'
				topDuals[gender][division][confName] = database.topDual(printout=False, teams=teams)
			
			wins = topDuals[gender][division][confName][2]
			losses = topDuals[gender][division][confName][3]
			teams = sorted(wins.items(), key=operator.itemgetter(1), reverse=True)
			meets = topDuals[gender][division][confName][1]
			for team in meets:
				meets[team] = str(meets[team])
		else:
			wins = None
			losses = None
			teams = None
			meets = None
		
		return render.duals(wins=wins, losses=losses, teams=teams, meet=meets, conferences=confList)


#HTML generators

def showMeet(scores):
	if scores == None: return None
	html='<h2 align="center">Simulated Results</h2>'
	html+='<table>'
	for event in eventOrder:
		if not event in scores: continue
		html += '<tr><th align="left" colspan=7>' + event + '</th></tr>'
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
	html += 'Show By: <select type="text" onchange="summaryType(this)">'
	html += '<option>swimmer</option> <option>event</option> <option>year</option>'
	html += '</select>'
	teams = {team: teamScores[team]['total'] for team in teamScores}
	for type in ['swimmer','event','year']:
		if type==showType: html += '<table id=' + type + '>'
		else: html += '<table class="hidden" id=' + type + '>'
		for team in sorted(teams, key=teams.__getitem__, reverse=True):
			html += '<tr> <th>'+team+'</th> </tr>'
			if not type in teamScores[team]: continue
			for name in sorted(teamScores[team][type], key=teamScores[team][type].__getitem__, reverse=True):
				html += '<tr>'
				html += '<td>'+name+'</td> <td>'+str(teamScores[team][type][name])+'</td>'
				html += '</tr>'
		html += '</table>'
	return html
	
if __name__ == "__main__":
	app.run()