import web
import meets
import operator
import re

eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","1 mtr Diving","3 mtr Diving"]
eventOrderInd = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley"]

urls = ('/', 'Home',
	'/swimulate', 'Swim',
	'/fantasy', 'Fantasy',
	'/conference', 'Conf',
	'/times', 'Times',
	'/duals', 'Duals',
	'/placing', 'Placing',
)

web.config.debug = False
database = meets.start(file='./swimData/DI15f', gender='Women')
database14 = None

gender = 'Women'
division = 'D1'

app = web.application(urls, globals())
render = web.template.render('templates/', base="layout")

def getTeamMeets(database):
	teamMeets = {}
	for team in database.teams:
		teamMeets[team]=[]
		for season in database.teams[team].meets:
			for meet in database.teams[team].meets[season]:
				meet = re.sub('\"', '\\\\\"', meet)
				teamMeets[team].append(meet)
	return teamMeets

def getConfList(database):
	conferences = database.conferences
	confList = conferences.keys()
	confList.sort()
	return confList

class Home():
	def GET(self):
		form = web.input(gender=None, division=None, _unicode=False)
		global gender, division
		change = False
		if form.gender and form.gender != gender:
			gender = form.gender
			change = True
		if form.division and form.division != division:
			division = form.division
			change = True
		if change:
			global database
			if division == 'D1':
				if gender == 'Men':
					database = meets.start(file='./swimData/DI15m', gender='Men')
				if gender == 'Women':
					database = meets.start(file='./swimData/DI15f', gender='Women')

			elif division == 'D2':

				if gender == 'Men':
					database = meets.start(file='./swimData/DII15m', gender='Men')
				if gender == 'Women':
					database = meets.start(file='./swimData/DII15f', gender='Women')
			else:
				if gender == 'Men':
					database = meets.start(file='./swimData/DIII15m', gender='Men')
				if gender == 'Women':
					database = meets.start(file='./swimData/DIII15f', gender='Women')

		return render.home(gender, division)

class Swim(object):
	def GET(self):
		teamMeets = getTeamMeets(database)
		
		form = web.input(team1=None, team2=None, meet1=None, meet2=None, _unicode=False)
		keys = form.keys()
		
		teamsMeets = {}
		for key in keys:
			num = int(key[-1])
			if not num in teamsMeets:
				teamsMeets[num]=[None, None]
			if "team" in key:
				teamsMeets[num][0]=form[key]
			elif "meet" in key:
				if form[key] in database.meets:
					teamsMeets[num][1]=database.meets[form[key]]
				else:
					teamsMeets[num][1] = form[key]

		#use topDual if no meet?
		remove=set()
		optimizeTeams = set()
		for num in teamsMeets:
			tm = teamsMeets[num]
			if not tm[0] or not tm[1]:
				remove.add(num)
			elif tm[1] == 'Create Lineup':
				optimizeTeams.add(tm[0])
				remove.add(num)
		for tm in remove:
			del(teamsMeets[tm])

		if len(teamsMeets)+len(optimizeTeams) < 1: return render.swimulator(teamMeets, scores=None, teamScores=None,
															   finalScores=None)
		
		else:
			newMeet = database.swimMeet(teamsMeets.values(), includeEvents=meets.requiredEvents, selectEvents=True,
										resetTimes=True)
			if optimizeTeams:
				newMeet = database.lineup(optimizeTeams, newMeet)
			if len(teamsMeets) > 2:
				showNum = 20
			else:
				showNum = 6	
			scores = newMeet.scoreString(showNum=showNum)
			teamScores = newMeet.scoreReport(printout=False)
				
			return render.swimulator(teamMeets=teamMeets, scores=showMeet(scores), teamScores=showTeamScores(
				teamScores), finalScores=showScores(scores))

class Fantasy(object):
	def GET(self):
		return render.fantasy()
		
class Conf(object):
	def GET(self):
		confList = getConfList(database)
		form = web.input(conference=None, taper=None, _unicode=False)
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
				conf = database.conferences[form.conference]
				confMeet = database.conference(teams=conf.teams, topTimes=topTimes)
				scores = confMeet.scoreString()
				teamScores = confMeet.scoreReport(printout=False)
		else:
			scores = None
			teamScores = None
		if teamScores:
			#with open('static/conf.json', 'w') as test:
			#	test.write(jsonEncode(teamScores))
			table = googleTable(teamScores, scores['scores'])
		else:
			table = ''
		return render.conference(conferences=confList, scores=showMeet(scores), teamScores=showTeamScores(teamScores), finalScores=showScores(scores), table=table)

class Times(object):
	def GET(self):
		confList = getConfList(database)
		form = web.input(conference=None, event=None, _unicode=False)
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
		confList = getConfList(database)
		
		form = web.input(conference=None)
		confName = form.conference
		
		if confName:
			if confName == 'All Teams':
				teams = 'all'
			else:
				teams = database.conferences[confName].teams
			topDuals = database.topDual(printout=False, teams=teams)
			
			wins = topDuals[2]
			losses = topDuals[3]
			teams = sorted(wins.items(), key=operator.itemgetter(1), reverse=True)
			meets = topDuals[1]
			for team in meets:
				meets[team] = str(meets[team])
		else:
			wins = None
			losses = None
			teams = None
			meets = None
		
		return render.duals(wins=wins, losses=losses, teams=teams, meet=meets, conferences=confList)

class Placing(object):
	def GET(self):
		global database14
		if not database14 or not database14.gender == gender:
			if gender == 'Women':
				database14 = meets.start(file='./swimData/DIII14f', gender='Women')
			else:
				database14 = meets.start(file='./swimData/DIII14m', gender='Men')

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
				if 'min' in key:
					times[num] += 60*int(form[key])
				elif 'sec' in key:
					times[num] += int(form[key])
				elif 'hun' in key:
					times[num] += .01*int(form[key])
				elif 'event' in key:
					events[num] = form[key]
			newSwims = set()
			for i in range(len(events)):
				if times[i] == 0:  # remove nonexistant swims
					continue
				elif improvement:
					times[i] *= 0.975
				newSwims.add((events[i], times[i]))
			if len(newSwims) > 0:
				confPlaces = database14.conferencePlace(division=division, gender=gender, newSwims=newSwims)
				confTable = showConf(confPlaces, newSwims)
			else:
				confTable = ''

		database = None  # return RAM

		return render.placing(conferences=confTable, events=eventOrder)

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
	html += 'Show By: <select type="text" onchange="summaryType(this)">'
	html += '<option>swimmer</option> <option>event</option> <option>year</option>'
	html += '</select>'
	html += '</form>'
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

def showConf(scores, newSwims):
	html = ''
	for conference in scores:
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
'''
def jsonEncode(teamScores):
	teams = {'name': 'flare', 'children': []}
	for team in teamScores:
		newTeam = {'name': team, 'children': []}
		for swimmer in teamScores[team]['swimmer']:
			newTeam['children'].append({'name': swimmer, 'size': teamScores[team]['swimmer'][swimmer]})
		teams['children'].append(newTeam)

	return json.dumps(teams)
'''

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
	del table[-1]
	return table

if __name__ == "__main__":
	app.run()