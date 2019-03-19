#!/usr/bin/env python
import web
import sqlmeets
import re
import time
import json
import os, urlparse
import hashlib
#from peewee import *

from operator import itemgetter
from fantasy import FantasyOwner, FantasyTeam, FantasyConference, FantasyScore, FantasyTeamSwimmer
from swimdb import TeamSeason, Meet, Meet, db, swimTime, Swimmer, Swim, swimTime
from events import eventOrder, eventConvert
from appsql import showMeet, showScores, showTeamScores


urls = ('/', 'Myteams',
	'/login', 'Login',
	'/logout', 'Logout',
	'/static/(.*)', 'Static',
	'/myteams', 'Myteams',
	'/roster', 'Roster',
	'/swimmers', 'Swimmers',
	'/join', 'Joinleague',
	'/standings', 'Standings',
	'/swimmerstats/(.+)', 'Swimmerstats',
	'/lineup', 'Lineup',
	'/matchup', 'Matchup',

)

# opens and then closes the db connections every time a user connects/disconnects
def connection_processor(handler):
	db.connect()
	try:
		return handler()
	finally:
		if not db.is_closed():
			db.close()


# retrieves all conference affiliations
def getConfs():
	confs = {'D1': {'Men': {}, 'Women': {}}, 'D2': {'Men': {}, 'Women': {}}, 'D3': {'Men': {}, 'Women': {}}}
	allTeams = {'Men': {'D1': set(), 'D2': set(), 'D3': set()}, 'Women': {'D1': set(), 'D2': set(), 'D3': set()}}
	for newTeam in TeamSeason.select(TeamSeason.team, TeamSeason.conference, TeamSeason.division,
									 TeamSeason.gender).distinct(TeamSeason.team):
		if newTeam.conference not in confs[newTeam.division][newTeam.gender]:
			confs[newTeam.division][newTeam.gender][newTeam.conference] = set()

		confs[newTeam.division][newTeam.gender][newTeam.conference].add(newTeam.team.strip())
		allTeams[newTeam.gender][newTeam.division].add(newTeam.team.strip())

	for division in ['D1', 'D2', 'D3']:
		allTeams['Men'][division] = list(allTeams['Men'][division])
		allTeams['Men'][division].sort()
		allTeams['Women'][division] = list(allTeams['Women'][division])
		allTeams['Women'][division].sort()

	return confs, allTeams

# gets the list of meets swum by a team in a given season
def getMeetList(gender='Women', division='D1', team=None, season=None):
	if not season:
		meets = {}
	else:
		meets = []

	for swim in Swim.select(Swim.meet, Swim.season).distinct().where(
			Swim.division==division, Swim.gender==gender, Swim.team==team):
		newSeason = swim.season
		newMeet = swim.meet
		newMeet.strip()

		if newSeason not in meets and not season:
			meets[newSeason] = []
		if not season:
			meets[newSeason].append(re.sub('\"', '\\\\\"', newMeet))
		else:
			if int(season)==int(newSeason):
				meets.append(re.sub('\"', '\\\\\"', newMeet))
	return meets

def current_teamid():
	try:
		return session.teamID
	except:
		return None

# set up web configuration
web.config.debug = False
app = web.application(urls, globals())
wsgiapp = app.wsgifunc()
session = web.session.Session(app, web.session.DiskStore('sessionsFantasy'),
							  initializer={'login': 0, 'teamid': None, 'userid': None})
render = web.template.render('templates/fantasy/', base="index", globals={'context': session})
app.add_processor(connection_processor)
#(conferences, allTeams) = getConfs()

currentSeason = 2018

# check to see if logged in
def logged():
	if session.login==1:
		return True
	else:
		return False


class Static():
	def GET(self, filename):
		try:
			if 'css' in filename:
				web.header("Content-Type", "text/css")
			elif 'js' in filename:
				web.header("Content-Type", "text/javascript")
			f = open('static/' + filename, 'r')
			return f.read()
		except:
			return


# shows current team and allows user to change
class Myteams():
	def GET(self):
		if not logged():
			raise web.seeother('/login')

		# update current team if a new one is chosen
		form = web.input(teamID=None)
		if session.teamid != form.teamID:
			try:
				session.teamID = FantasyTeam.get(id=form.teamID).id
			except:
				pass
		if hasattr(session, 'teamID'):
			print 'current team', session.teamID
		# return my possible teams
		teams = []
		user = FantasyOwner.get(id=session.userid)
		for team in FantasyTeam.select().where(FantasyTeam.owner==user):
			teams.append((team.name, team.id))
		print teams
		try:
			teamID = session.teamID
		except AttributeError:
			teamID = None

		return render.myteams(teams, teamID)


class Roster():
	def GET(self):
		if not logged():
			raise web.seeother('/login')

		try:
			myTeam = FantasyTeam.get(id=session.teamID)
		except:
			return render.roster('')

		return render.roster(showTeam(myTeam))


class Swimmers():
	def GET(self):
		if not logged():
			raise web.seeother('/login')
		try:
			myTeam = FantasyTeam.get(id=session.teamid)
		except:
			return render.swimmers('')
		return render.swimmers(showSwimmers(conference=myTeam.conference))

	def POST(self):
		form = web.input(drop=False)
		myTeam = FantasyTeam.get(id=session.teamid)
		swimmer = FantasyTeamSwimmer.get(id=form.swimmer)
		if form.drop:
			status = myTeam.dropSwimmer(swimmer)
		else:
			status = myTeam.addSwimmer(swimmer)

		# refresh page to show updates, return error?
		return self.GET()


class Joinleague():
	def GET(self):
		if not logged():
			raise web.seeother('/login')

		form = web.input()
		league = FantasyConference.get()
		return render.joinleague([(league.name, league.id)])

	def POST(self):
		form = web.input(leagueid=None, division=None, conference=None, gender=None, teamname=None, join=None)

		# join existing conference
		if form.teamname and form.join and form.leagueid:
			user = FantasyOwner.get(id=session.userid)
			myConf = FantasyConference.get(id=form.leagueid)
			print 'joining league', user, myConf, form.teamname
			try:
				myTeam = FantasyTeam(conference=myConf, owner=user, name=form.teamname)
				myTeam.save()
				session.teamid = myTeam.id
				return render.lineup()
			except:
				leagues = []
				for league in FantasyConference.select():
					leagues.append(league.name, league.id)
				return render.joinleague(league)

		# TODO still need to handle creating a new conference

class Matchup():
	def GET(self):
		form = web.input(month=0)
		team = FantasyTeam.get(id=session.teamid)
		months = team.conference.getDates()
		if int(form.month) not in months:
			return render.matchup(months)

		meet, bench = team.dual(month=form.month, verbose=False)
		if meet:
			meet_html = showMeet(meet.scoreString())
			team_scores_html = showTeamScores(meet.scoreReport())
			score_breakdown = showScores(meet.scoreString())
		else:
			meet_html = ''
		if bench:
			bench_html = showMeet(bench.scoreString(showScores=False))
		else:
			bench_html = ''

			scores = meet.scoreString(showNum=25)

		return render.matchup(months, meet_html, bench_html, team_scores_html, score_breakdown)

	def POST(self):
		data = json.loads(web.data)


class Logout():
	def GET(self):
		session.kill()
		raise web.seeother('/login')


class Login():
	def GET(self):
		return render.login()

	def POST(self):
		name, passwd = web.input().user, web.input().passwd
		action = web.input(action='').action

		# create a new user if it doesn't exist already
		if action=='Create New' and name and passwd:
			try:
				newUser = FantasyOwner(name=name, password=passwd)
				newUser.save()
			except:
				return render.login()
			session.login = 1
			session.userid = newUser.id
			raise web.seeother('/myteams')

		# try to log the current user in with the info and set session information
		try:  # check username
			user = FantasyOwner.get(name=name)
			print name, passwd, user.name, user.password
		except:
			print 'user does not exist'
			session.login = 0
			return render.login()

		if user.password == passwd: # check password
			# hashlib.sha1("sAlt101"+passwd).hexdigest() == ident['pass']:
			# no salt or hash for testing
			session.login = 1
			session.userid = user.id

			# default their first fantasy team if they have one
			try:
				session.teamid = FantasyTeam.get(owner=user.id).id
			except FantasyTeam.DoesNotExist:
				pass
			raise web.seeother('/myteams')
		else:
			print 'bad pwd'
			session.login = 0
			return render.login()


class Swimmerstats():
	def GET(self, swimmerid):
		swimmer = Swimmer.get(id=swimmerid)
		return render.swimmerstats(showSwimmer(swimmer))

# HTML generation
def showTeam(team):
	html = ''
	html += '<h1>' + team.name + '</h1>'
	html += '<table class="fantasyswimmers">'
	for fanswimmer in team.swimmers():
		swimmer = fanswimmer.swimmer
		html += '<tr>'
		html += '<td class="name"> <a href="/swimmerstats/' + str(swimmer.id) + '">' + swimmer.name + '</td>'
		html += '<td>' + swimmer.year + '</td>'
		html += '<td>' + swimmer.team.team + '</td>'
		html += '<td><button id="' + str(fanswimmer.id) + '">Drop</button></td>'
	html += '</table>'
	return html

def showSwimmers(conference):
	html = ''
	html += '<h2>' + conference.name + ' Swimmers' + '<h2>'
	html += '<table class="fantasyswimmers">'
	html += '<thead><tr>'
	html += '<th>Name</th>'
	html += '<th>Team</th>'
	html += '<th>Fantasy Team</th>'
	html += '<th>Year</th>'
	html += '<th>Power Score</th>'
	html += '<th>Top Events</th>'
	html += '</tr></thead>'
	html += '<tbody>'
	for fanswimmer in conference.swimmers():
		swimmer = fanswimmer.swimmer
		score = swimmer.getPPTs()
		html += '<tr>'
		html += '<td class="name"> <a href="/swimmerstats/' + str(swimmer.id) + '">' + swimmer.name + '</td>'
		html += '<td>' + swimmer.team.team + '</td>'
		html += '<td>' + fanswimmer.team.name + '</td>'
		html += '<td>' + swimmer.year + '</td>'
		html += '<td>' + str(int(score)) + '</td>'
		#topSwims = swimmer.getTaperSwims()
		#swimStr =''
		#for event in topSwims:
		#	swimStr += event + ': <b>' + swimTime(topSwims[event].time)\
		#			   + ' (' + str(int(topSwims[event].getPPTs())) + ')</b> <br> '
		swimStr = ''
		html += '<td>' + swimStr + '</td>'
		html += '<td><button id="' + str(fanswimmer.id) + '">Add</button></td>'
		html += '</tr>'

	html += '</tbody>'
	html += '</table>'
	return html

def showSwimmer(swimmer):
	html = ''
	html += '<h1>' + swimmer.name + '</h1>'
	html += '<h2>' + swimmer.year + '</h2>'
	html += '<h2>' + swimmer.team.team + '</h2>'
	html += '<table>'
	html += '<tr>'
	html += '<th>Date</th> <th>Event</th> <th>Time</th> <th>Meet</th> <th>Points</th>'
	html += '</tr>'
	for swim in Swim.select().where(Swim.swimmer==swimmer).order_by(Swim.date):
		html += '<tr>'
		html += '<td>' + str(swim.date) + '</td>'
		html += '<td>' + swim.event + '</td>'
		html += '<td>' + swimTime(swim.time) + '</td>'
		html += '<td>' + swim.meet + '</td>'
		html += '<td>' + str(int(swim.getPPTs())) + '</td>'
		html += '</tr>'
	html += '</table>'

	return html

if __name__ == "__main__":
	app.run()
