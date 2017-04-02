import time
import re
import os
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from unidecode import unidecode

eventsSCY = ['1650 Free', '500 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

eventsSCM = ['1500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'100 IM', '200 IM', '400 IM']

eventsLCM = ['1500 Free', '400 Free', '200 Free', '100 Free', '50 Free',
				'50 Fly', '100 Fly', '200 Fly',
				'50 Back', '100 Back', '200 Back',
				'50 Breast', '100 Breast', '200 Breast',
				'200 IM', '400 IM']

def init_driver():
	driver = webdriver.Chrome()
	driver.wait = WebDriverWait(driver, 5)
	return driver


# converts to a time in seconds
def toTime(time):
	if time[0]=="X" or time[0]=="x":
		time=time[1:]
	if time[len(time)-1]=="r" or time[len(time)-1]=="R":
		time=time[0:len(time)-1]
	if re.match(".*:.*",time) == None:
		return time
	return float(re.split(":",time)[0])*60 +float(re.split(":",time)[1])


def lookup(driver, gender="M", event="50 Free", courseStr="LCM", bestAll="Best", nTimes="7000", year="2016", File=None,
		   minAge='All', maxAge='All', zone=None, oldTimes=set()):
	driver.get('http://www.usaswimming.org/DesktopDefault.aspx?TabId=1482&Alias=Rainbow&Lang=en')
	if(gender=="M"):
		sex="radMale"
		genderOut="Men"
	else:
		sex = "radFemale"
		genderOut = "Women"
	distance = event[0:event.find(" ")]
	strke = event[event.find(" ") + 1:]
	strokeDict = {"Free": 1, "Back": 2, "Breast": 3, "Fly": 4, "IM": 5}
	stroke = strokeDict[strke]
	courseDict = {"SCY": 1, "SCM": 2, "LCM": 3}
	course = courseDict[courseStr]
	bestAllDict = {"All": "radAllTimesForSwimmer", "Best": "radBestTimeOnly"}
	bestAll = bestAllDict[bestAll]
	yearDict = {"1996":"1","1997":"2","1998":"3","1999":"4","2000":"5","2001":"6","2002":"7","2003":"8","2004":"9",
			   "2005":"10","2006":"11","2007":"12","2008":"13","2009":"14","2010":"15","2011":"16","2012":"17","2013":"18","2014":"19","2015":"20","2016":"21"}
	year = yearDict[year]

	for page in range(0, int(nTimes)/50):
		try:
			if page == 0:
				driver.find_element_by_xpath("//select[@id='ctl68_ddNamedDateRange']/option[@value="+year+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddDistance']/option[@value="+distance+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddStroke']/option[@value="+str(stroke)+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddCourse']/option[@value="+str(course)+"]").click()
				driver.find_element_by_xpath("//input[@id='ctl68_" + sex + "']").click()
				driver.find_element_by_xpath("//input[@id='ctl68_radlStandard_14']").click()
				driver.find_element_by_xpath("//input[@id='ctl68_" + bestAll + "']").click()
				driver.find_element_by_id("ctl68_txtMaxResults").clear()
				driver.find_element_by_id("ctl68_txtMaxResults").send_keys(nTimes)
				if zone:
					driver.find_element_by_xpath("//select[@id='ctl68_ddZone']/option[@value=" + zone + "]").click()
				if minAge!="All":
					driver.find_element_by_xpath("//select[@id='ctl68_ddAgeStart']/option[@value="+minAge+"]").click()
				if maxAge!="All":
					driver.find_element_by_xpath("//select[@id='ctl68_ddAgeEnd']/option[@value="+maxAge+"]").click()
				driver.find_element_by_id("ctl68_btnSearch").click()

			if page > 0:
				try:
					driver.find_element_by_link_text(str(page+1)).click()
				except WebDriverException:
					try:
						if len(driver.find_elements_by_link_text("..."))>1:
							driver.find_elements_by_link_text("...")[1].click()
						else:
							if page==30:
								driver.find_element_by_link_text("...").click()
							else:
								break
					except WebDriverException:
						break
			time.sleep(3.5)
			r=driver.page_source
		except TimeoutException:
			print("Error")

		place = r.find('<td>Meet Results</td>') + 25
		end = r.find('</table>', place + 1000)
		count = 0
		previousResult = ""

		# there are vastly more efficient ways to loop through this, but this code is done and works, so I don't care
		while place > 0:
			place = r.find('</td>', place + 1, end)
			count = (count + 1) % 12
			if count == 1:
				timeMMSS = r[r.find('>',place+5)+1:r.find('<',place+9)]
				if len(timeMMSS) == 0:
					break
			if count == 4:
				place = r.find('<span',place+1,end)
				swimmer = r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count == 8:
				team = r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count == 6:
				age = r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count == 5:
				fore = r[r.find('>',place+5)+1:r.find('<',place+9)]
				if len(fore)==0:
					foreign = ""
				else:
					foreign = fore
			if count == 9:
				place = r.find('<span',place+1,end)
				meet = r[r.find('>',place+5)+1:r.find('<',place+9)-8]
				date = r[r.find('<',place+9)-8:r.find('<',place+9)]
				# the web page sometimes returns the same result a bunch of times in a row.
				# this throws a time out if it repeats the swimmer name age time and date of the row above.
				# also throws out the header row
				if timeMMSS=='Time' or previousResult == swimmer+age+timeMMSS+date:
					continue
				previousResult = swimmer + age + timeMMSS + date
				if not swimmer:
					continue
				outputstring = meet+'\t'+swimmer+'\t'+age+'\t'+team+'\t'+genderOut+'\t'+event+'\t'+str(toTime(
					timeMMSS))+'\t'+timeMMSS+'\t'+date+'\t'+courseStr+'\t'+'\n'
				outputstring = unidecode(outputstring)
				outputstring = str(outputstring).translate(None, "#")
				outputstring= outputstring.replace("'", "")

				if outputstring not in oldTimes:  # make sure the time doesn't already exist
					File.write(outputstring)
					oldTimes.add(outputstring)


if __name__ == "__main__":
	basedirectory = 'data/club'
	driver = init_driver()
	years = ['2016']#, '2015']  # ['2013', '2012']
	genders = ['M', 'F']
	course = 'LCM'
	if course=='SCY':
		events = eventsSCY
	elif course=='SCM':
		events = eventsSCM
	elif course=='LCM':
		events = eventsLCM

	#events = ['100 Free']
	#zones = ['1', '2', '3', '4']
	zones = ['All']
	#ages = range(22, 30)
	ages = ['22-30']

	for gender in genders:
		for event in events:
			for year in years:
				for age in ages:
					for zone in zones:
						directory = basedirectory + '/' + year + '/' + str(age)
						if not os.path.exists(directory):
							os.makedirs(directory)

						filename = 'Club_' + year + '_' + course + '_' + gender + '_' + event + '_Age_' + str(age) + \
								   '_' + zone
						print filename
						filepath = directory + '/' + filename

						# load old times to prevent dups
						oldTimes = set()
						if os.path.exists(filepath):
							with open(filepath, 'r') as oldMeetFile:
								for line in oldMeetFile:
									oldTimes.add(line)

						with open(filepath, 'a+') as meetFile:
							try:
								lookup(driver, event=event, courseStr=course, gender=gender, year=year, File=meetFile,
							   		minAge='22', maxAge='30', zone=None, oldTimes=oldTimes)
							except:
								print 'Error'
							finally:
								print 'OK'
	time.sleep(5)
	driver.quit()