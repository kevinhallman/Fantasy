import web
import meets
import os
import operator
import re

eventOrder=["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle",'500 Yard Freestyle','1000 Yard Freestyle',"1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay","1 mtr Diving","3 mtr Diving"]

urls = (
  '/', 'Swim',
  '/swimulate','Swim',
  '/fantasy','Fantasy',
  '/conference','Conf',
  '/times','Times',
  '/topDuals','Duals',
)

app = web.application(urls, globals())

render = web.template.render('templates/', base="layout")

meets.start(file='./bin/D3_15_12-8',gender='Men')
database=meets.database
topDuals = {}

teamMeets = {}
for team in database.teams:
	teamMeets[team]=[]
	for season in database.teams[team].meets:
		for meet in database.teams[team].meets[season]:
			meet = re.sub('\"','\\\\\"',meet)
			teamMeets[team].append(meet)


conferences = database.conferences
confList = conferences.keys()
confList.sort()

class Swim(object):
	def GET(self):
		form = web.input(team1='',team2='')
		if form.team1=='' or form.team2=='':
			return render.swimulator(teamMeets,scores=None,fail=True,team1=None,team2=None,teamScores=None,finalScores=None)
		
		else:
			team1 = database.teams[form.team1]
			team2 = database.teams[form.team2]
			if form.meet1 != "Create Lineup":	
				meet1 = database.meets[form.meet1] #team1.topDual(meets.Season(2014),database = database)
			else:
				meet1 = form.meet1
			if form.meet2 != "Create Lineup":
				meet2 = database.meets[form.meet2] #team2.topDual(meets.Season(2014),database = database)
			else:
				meet2 = form.meet2
			
			newMeet = None
			if meet1 == None or meet2 == None:
				scores = None
				fail = "Both teams haven't swum yet"
			elif meet1 == "Create Lineup" and meet2 == "Create Lineup": 
				scores = None
				fail = "That's tricky"
			elif meet1 == "Create Lineup":
				newMeet = database.lineup(team2,team1,meet2,resetTimes=True)
			elif meet2 == "Create Lineup":
				newMeet = database.lineup(team1,team2,meet1,resetTimes=True)
			else:
				newMeet = database.swimMeet([[team1,meet1],[team2,meet2]],includeEvents=meets.requiredEvents,selectEvents=True,resetTimes=True)

			if newMeet != None:
				scores = newMeet.scoreString(showNum=6)
				teamScores = newMeet.scoreReport(printout=False)
				fail = False
			else:
				teamScores = None
			return render.swimulator(teamMeets = teamMeets,scores = showMeet(scores),fail = fail,team1=team1,team2=team2,teamScores=showTeamScores(teamScores),finalScores=showScores(scores))

class Fantasy(object):
	def GET(self):
		return render.fantasy()
		
class Conf(object):
	def GET(self):
		form = web.input(conference=None)
		if form.conference:
			if form.conference == 'Nationals':
				confMeet = database.conference2(teams=database.teams.keys())
				scores = confMeet.scoreString(25)
				teamScores = confMeet.scoreReport(printout=False)
			else:
				conf = database.conferences[form.conference]
				confMeet = database.conference2(teams=conf.teams)
				scores = confMeet.scoreString()
				teamScores = confMeet.scoreReport(printout=False)
		else:
			scores = None
			teamScores = None
		return render.conference(conferences=confList,scores = showMeet(scores),teamScores = showTeamScores(teamScores),finalScores=showScores(scores))
		
class Times(object):
	def GET(self):
		return render.times()

class Duals(object):
	def GET(self):
		form = web.input(conference=None)
		confName = form.conference
		
		if confName:
			#cache
			global topDuals
			if not confName in topDuals:
				if confName in database.conferences:
					teams = database.conferences[confName].teams
				else:
					teams = 'all'
				topDuals[confName] = database.topDual(printout=False,teams = teams) #results,meets,wins,losses
			
			wins = topDuals[confName][2]
			losses = topDuals[confName][3]
			teams = sorted(wins.items(),key=operator.itemgetter(1),reverse=True)
			meet = topDuals[confName][1]
		else:
			wins = None
			losses = None
			teams = None
			meet = None
		
		return render.duals(wins = wins,losses = losses,teams = teams,meet = meet,conferences = confList)
		
#HTML generators

def showMeet(scores):
	if scores == None: return None
	html='<h2 align="center">Simulated Results</h2>'
	
	html+='<table>'
	for event in eventOrder:
		if not event in scores: continue
		html += '<tr><th align="left" colspan=7>'+event+'</th></tr>'
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
	
def showTeamScores(teamScores):
	if teamScores == None: return None
	html = 	'<h2 align="center">	Score Report </h2>'
	html += '<table>'
	for team in teamScores:
		html += '<tr> <th>'+team+'</th> </tr>'
		for name in teamScores[team]:
			if name[0] == 'Total': continue
			html += '<tr>'
			html += '<td>'+name[0]+'</td> <td>'+str(name[1])+'</td>'
			html += '</tr>'
	html += '</table>'
	return html
	
if __name__ == "__main__":
	app.run()