__author__ = 'hallmank'

from peewee import *
import os
import re
from datetime import date

db = PostgresqlDatabase('swimdb', user='hallmank')


class BaseModel(Model):
	class Meta:
		database = db # This model uses the "people.db" database.


class Swim(BaseModel):
	name = CharField()
	date = DateField()
	time = TimeField()
	season = IntegerField()
	team = CharField()
	meet = CharField()
	gender = CharField()
	conference = CharField()
	division = CharField()
	relay = BooleanField()

	class Meta:
		order_by = ('-time',)
		indexes = ('name', 'season', 'team', 'meet', 'gender')


def seasonString(dateString):
	dateParts = re.split('/', dateString)
	year = int(dateParts[2])
	month = int(dateParts[0])
	day = int(dateParts[1])
	d = date(year, month, day)

	if d > date(d.year, 4, 1):
		year = d.year
	else:
		year = d.year - 1
	return year, date

#load the swims
swims = []
lineNum = 0
root = './swimData'
for swimFileName in os.listdir(root):
	if swimFileName[0]=='.':
		continue  # don't use ref files
	with open(root + '/' + swimFileName) as swimFile:
		for line in swimFile:
			lineNum += 1
			if lineNum > 3:
				break
			swimArray = re.split('\t', line)
			meet = swimArray[0].strip()
			d = swimArray[1]
			(season, swimDate) = seasonString(d)
			name = swimArray[2]
			year = swimArray[3]
			team = swimArray[4]
			gender = swimArray[5]
			event = swimArray[6]
			time = '0:' + str(swimArray[7].strip())
			if 'Relay' in event:
				relay = True
			else:
				relay = False

			if relay:
				name = team + ' Relay'

			newSwim = {'meet': meet, 'date': swimDate, 'season': season, 'name': name, 'year': year, 'team': team,
					   'gender': gender, 'event': event, 'time': time}

			swims.append(newSwim)

print swims

with db.transaction():
	Model.insert_many(swims).execute()