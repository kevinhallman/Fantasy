import web
import meets
import os

urls = (
  '/', 'Swim',
  '/swimulate','Swim',
  '/fantasy','Fantasy',
  '/conference','Conf',
  '/times','Times',
)

app = web.application(urls, globals())

render = web.template.render('templates/', base="layout")

meets.start(file='./bin/D3_15_11-24',gender='Women')
database=meets.database


teamMeets = {}
for team in database.teams:
	teamMeets[team]=[]
	for season in database.teams[team].meets:
		for meet in database.teams[team].meets[season]:
			teamMeets[team].append(meet)

conferences = database.conferences

class Swim(object):
	def GET(self):
		return render.swimulator(teamMeets,scores=None,fail=True,team1=None,team2=None,teamScores=None)

	def POST(self):
		form = web.input()
		if form.team1=='' or form.team2=='':
			return render.swimulator(teamMeets,scores=None,fail=True,team1=None,team2=None,teamScores=None)
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
			print team1,team2
			return render.swimulator(teamMeets = teamMeets,scores = scores,fail = fail,team1=team1,team2=team2,teamScores=teamScores)

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
		confList = conferences.keys()
		confList.sort()
		return render.conference(conferences=confList,scores = scores,teamScores = teamScores)
		
class Times(object):
	def GET(self):
		return render.times()

if __name__ == "__main__":
	app.run()