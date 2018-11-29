import unittest
import requests


class CheckBaseURLs(unittest.TestCase):
	def test_home(self):
		resp = requests.get('http://localhost:8080/home',
                         data={'arg': 'value'})
		assert resp.status_code == 200


	def test_swimulate(self):
		resp = requests.get('http://localhost:8080/swimulate?division1=D1&team1=Alabama&season1=2018&meet1='
				'Create+Lineup&division2=D1&team2=Arkansas&season2=2018&meet2=Create+Lineup&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_swimulateJSON(self):
		resp = requests.get('http://localhost:8080/swimulateJSON?division1=D1&team1=Alabama&season1=2018&meet1=Create'
							'+Lineup&division2=D1&team2=Arkansas&season2=2018&meet2=Create+Lineup&gender=Women&division=D1')

		assert resp.status_code == 200

	def test_conference(self):
		resp = requests.get('http://localhost:8080/conference?conference=Big+12&season=2018&taper=Top+Time'
									'&date=Whole+Season&heats=16&size=17&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_conferenceJSON(self):
		resp = requests.get('http://localhost:8080/conferenceJSON?conference=Big+12&season=2018&taper=Top+Time'
									'&date=Whole+Season&heats=16&size=17&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_improvement(self):
		resp = requests.get('http://0.0.0.0:8080/improvement?conference=Atlantic+10&season=2017&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_improvementJSON(self):
		resp = requests.get('http://0.0.0.0:8080/improvementJSON?conference=Atlantic+10&season=2017&gender=Women'
							'&division=D1')
		assert resp.status_code == 200

	def test_rankings(self):
		resp = requests.get('http://0.0.0.0:8080/rankings?conference=Big+12&season=2018&gender=Women&dual=Invite&division=D1')
		assert resp.status_code == 200

	def test_rankingsJSON(self):
		resp = requests.get('http://0.0.0.0:8080/rankingsJSON?conference=Big+12&season=2018&gender=Women&dual=Invite'
							'&division=D1')
		assert resp.status_code == 200

	def test_programs(self):
		resp = requests.get('http://0.0.0.0:8080/programs?conference=All&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_programsJSON(self):
		resp = requests.get('http://0.0.0.0:8080/programsJSON?conference=All&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_preseason(self):
		resp = requests.get('http://0.0.0.0:8080/preseason?gender=Women&division=D1')
		assert resp.status_code == 200

	def test_preseasonJSON(self):
		resp = requests.get('http://0.0.0.0:8080/preseasonJSON?gender=Men&division=D1')
		assert resp.status_code == 200

	def test_teamstats(self):
		resp = requests.get('http://0.0.0.0:8080/teamstats/Michigan?gender=Women&division=D1')
		assert resp.status_code == 200

	def test_teamstatsJSON(self):
		resp = requests.get('http://0.0.0.0:8080/teamstatsJSON/Michigan?gender=Women&division=D1')
		assert resp.status_code == 200

	def test_powerscore(self):
		resp = requests.get('http://0.0.0.0:8080/powerscore?event=50+Free&min=0&sec=25&hun=00&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_taper(self):
		resp = requests.get('http://0.0.0.0:8080/taper?conference=Big+Ten&season=2017&gender=Women&toptime=Top+Time&division=D1')
		assert resp.status_code == 200

	def test_taperJSON(self):
		resp = requests.get('http://0.0.0.0:8080/taperJSON?conference=Big+Ten&season=2017&gender=Women&toptime=Top+Time'
							'&division=D1')
		assert resp.status_code == 200

	def test_topswimmers(self):
		resp = requests.get('http://0.0.0.0:8080/swimmer?gender=Women&division=D1')
		assert resp.status_code == 200

	def test_topswimmersJSON(self):
		resp = requests.get('http://0.0.0.0:8080/swimmerJSON?gender=Women&division=D1')
		assert resp.status_code == 200

	def test_timeconvert(self):
		resp = requests.get('http://0.0.0.0:8080/timeconvert?event=100+Free&fromcourse=LCM&tocourse=SCY'
							'&fromage=Open&min=1&sec=00&hun=00&gender=Women&division=D1&submit=Calculate')
		assert resp.status_code == 200

	'''
	def test_teamMeets(self):
		resp = requests.get('http://0.0.0.0:8080/improvement?conference=Atlantic+10&season=2017&gender=Women&division=D1')
		assert resp.status_code == 200

	def test_getConfs(self):
		self.app.request('/getConfs')

	def test_getTeams(self):
		self.app.request('/getTeams')
	'''

if __name__=='__main__':
	unittest.main()
