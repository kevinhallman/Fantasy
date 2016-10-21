from peewee import *
import os
import re
from datetime import date as Date
import time as Time
import urlparse
from playhouse.migrate import *
from swimdb import Swim, Swimmer, TeamSeason, toTime


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


class Clubswimmer(Swimmer):
	age = IntegerField()
	season = IntegerField(null=True)
	year = IntegerField(null=True)
	class Meta:
		database = db

class Clubswim(Swim):
	clubswimmer = ForeignKeyField(Clubswimmer, null=True)
	course = CharField()
	age = IntegerField()
	timeStr = CharField()
	season = IntegerField(null=True)
	conference = CharField(null=True)
	division = CharField(null=True)

	class Meta:
		database = db

class Clubteamseason(TeamSeason):
	class Meta:
		database = db


def importSwims(loadSwims=True, loadSwimmers=True):
	root = 'agegroup'

	for fileName in os.listdir(root):
		if not 'Club' in fileName: continue

		parts = re.split('_', fileName)
		print parts
		_, data, _, age, region = parts[0], parts[1], parts[2], parts[3], parts[4]
		year, course, gender, event = data[:4], data[4:7], data[7:8], data[8:]

		print year, course, gender, event, age, region

		'2016 ILCL BNSC MARCH TIME TRIA 	Malinowski, Kenna	8	Bloomington Normal Swim Club	Women	100 Free	65.32	1:05.32	03/05/16	SCY'
		i=0
		with open(root + '/' + fileName) as file:
			swims = []
			swimmers = []
			swimmerKeys = set()

			for line in file:
				i+=1
				if i%100==0:
					pass
					#print i
				swimParts = re.split('\t', line)
				#print swimParts
				if len(swimParts)<5: continue
				meet, name, age, team, gender, event, seconds, timeStr, date = swimParts[0], swimParts[1], swimParts[
					2], swimParts[3], swimParts[4], swimParts[5], swimParts[6], swimParts[7], swimParts[8]

				#print meet, name, age, team, gender, event, seconds, timeStr, date
				time = toTime(timeStr)

				if loadSwimmers:
					key = str(age) + name + year + team + gender
					if not key in swimmerKeys:
						swimmerKeys.add(key)
						#try:
						#	swimmerID = Clubswimmer.get(Clubswimmer.age==age, Clubswimmer.name==name,
						# Clubswimmer.team==team).id
						#except Clubswimmer.DoesNotExist:
						newSwimmer = {'name': name, 'age': age, 'team': team, 'gender': gender}
						swimmers.append(newSwimmer)

				if loadSwims:
					'''
					try:
						Clubswim.get(Clubswim.name==event, Clubswim.timeStr==timeStr, Clubswim.event==event,
							Clubswim.date==date)  # floats in SQL and python evidently different precision
					except Clubswim.DoesNotExist:
						#if not swimmerID:
					'''
					swimmerID = Clubswimmer.get(Clubswimmer.age==age, Clubswimmer.name==name, Clubswimmer.team==team).id
					newSwim = {'meet': meet, 'date': date, 'age': int(age), 'name': name, 'year': int(year),
								   'team': team, 'gender': gender, 'event': event, 'time': seconds, 'timeStr':
									   timeStr, 'relay': False, 'course': course, 'clubswimmer':swimmerID}
					swims.append(newSwim)


		#print swims, swimmers

		db.connect()
		if loadSwims and len(swims) > 0:
			print 'Swims:', len(swims)
			print Clubswim.insert_many(swims).execute()

		if loadSwimmers and len(swimmers) > 0:
			print 'Swimmers:', len(swimmers)
			print Clubswimmer.insert_many(swimmers).execute()

if __name__== '__main__':
	#db.drop_tables([Clubswim])
	#db.drop_tables([Clubswimmer])
	#db.create_tables([Clubswimmer])
	#db.create_tables([Clubswim])
	importSwims(loadSwims=False)
	importSwims(loadSwimmers=False)



