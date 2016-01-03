import sqlmeets
import re
import os, urlparse
import numpy
from peewee import *
from operator import itemgetter

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
	'/teamMeets', 'teamMeets',
	'/programs', 'Programs'
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



conferences = getConfs('data/conferences.txt')
database = sqlmeets.SwimDatabase(database=db)

teams = []
teamRecruits = {}
teamImprovement = {}
teamAttrition = {}
for gender in ['Men', 'Women']:
	for division in conferences:
		for conf in conferences[division]:
			for team in conferences[division][conf]:
				if team != 'Richmond' and team!= 'Connecticut': continue

				#get recruit scores
				invScore = database.topTeamScore(team, gender=gender, recruits=False, division=division, season=2015,
									 dual=False)
				dualScore = database.topTeamScore(team, gender=gender, recruits=False, division=division, season=2015,
											 dual=True)

				#get attrition rate
				attrition = database.attrition([team], gender=gender)
				if attrition == {}:
					attrition = 0
				else:
					attrition = -attrition

				#get improvement
				drops = database.improvement2(teams=[team], gender=gender, season1=2015, season2=2012)
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
					teams.append(newTeam)
				print team
print teams


Team.delete().where(Team.name=='Richmond')
Team.delete().where(Team.name=='Connecticut')

db.connect()
with db.transaction():
	Team.insert_many(teams).execute()


