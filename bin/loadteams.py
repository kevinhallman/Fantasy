import sqlmeets
import os, urlparse
import numpy
from peewee import *
from swimdb import TeamSeason

eventOrder = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley","200 Yard Medley Relay","400 Yard Medley Relay","200 Yard Freestyle Relay","400 Yard Freestyle Relay","800 Yard Freestyle Relay"]
eventOrderInd = ["50 Yard Freestyle","100 Yard Freestyle","200 Yard Freestyle","500 Yard Freestyle","1000 Yard Freestyle","1650 Yard Freestyle","100 Yard Butterfly","200 Yard Butterfly","100 Yard Backstroke","200 Yard Backstroke","100 Yard Breastroke","200 Yard Breastroke","200 Yard Individual Medley","400 Yard Individual Medley"]

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

#db.drop_tables([Team])
#db.create_tables([Team])


(conferences, allTeams) = getConfs()
database = sqlmeets.SwimDatabase(database=db)

teams = []
teamRecruits = {}
teamImprovement = {}
teamAttrition = {}

for division in conferences:
	for gender in conferences[division]:
		for conf in conferences[division][gender]:
			for team in conferences[division][gender][conf]:
				#if team != 'Richmond' and team!= 'Connecticut': continue

				# get team score
				invScore = database.topTeamScore(team, gender=gender, recruits=False, division=division, season=2016,
									 dual=False)
				dualScore = database.topTeamScore(team, gender=gender, recruits=False, division=division, season=2016,
											 dual=True)

				# get attrition rate
				attrition = database.attrition([team], gender=gender)
				if attrition == {}:
					attrition = 0
				else:
					attrition = -attrition

				# get improvement
				drops = database.improvement2(teams=[team], gender=gender, season1=2016, season2=2011)
				if drops != {}:
					improvement = numpy.mean(drops)
				else:
					improvement = 0
				if invScore != 0 or attrition != 0 or improvement != 0:
					teamRecruits[team] = invScore
					teamAttrition[team] = attrition
					teamImprovement[team] = improvement

					newTeam = {	'name': team,
						'improvement': improvement,
						'attrition': attrition,
						'strengthdual': dualScore,
						'strengthinvite': invScore,
						'conference': conf,
						'division': division,
						'gender': gender}

					if not Team.update(attrition=attrition, strengthdual=dualScore, strengthinvite=invScore,
							improvement=improvement).where(Team.name==team, Team.gender==gender, Team.conference==conf,
														   Team.division==division):
						teams.append(newTeam)
				print team, attrition, improvement, invScore
print teams


#Team.delete().where(Team.name=='Richmond')
#Team.delete().where(Team.name=='Connecticut')

db.connect()
with db.transaction():
	Team.insert_many(teams).execute()


