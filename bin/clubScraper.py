import time
import re
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from unidecode import unidecode

def init_driver():
	driver = webdriver.Chrome()
	driver.wait = WebDriverWait(driver, 5)
	return driver

#convers to a time in seconds
def toTime(time):
	if time[0]=="X" or time[0]=="x":
		time=time[1:]
	if time[len(time)-1]=="r" or time[len(time)-1]=="R":
		time=time[0:len(time)-1]
	if re.match(".*:.*",time) == None:
		return time
	return float(re.split(":",time)[0])*60 +float(re.split(":",time)[1])

def lookup(driver, gender="M",event="50 Free",course="LCM",bestAll="All",nTimes="6000",year="2016",File='',minAge='All',maxAge='All'):
	driver.get('http://www.usaswimming.org/DesktopDefault.aspx?TabId=1482')
	if(gender=="M"):
		sex="radMale"
		genderOut="Men"
	else:
		sex = "radFemale"
		genderOut = "Women"
	distance = event[0:event.find(" ")]
	strke = event[event.find(" ")+1:]
	strokeDict = {"Free":1,"Back":2,"Breast":3,"Fly":4,"IM":5}
	stroke = strokeDict[strke]
	courseDict = {"SCY":1,"SCM":2,"LCM":3}
	course = courseDict[course]
	bestAllDict = {"All":"radAllTimesForSwimmer","Best":"radBestTimeOnly"}
	bestAll = bestAllDict[bestAll]
	yearDict = {"1996":"1","1997":"2","1998":"3","1999":"4","2000":"5","2001":"6","2002":"7","2003":"8","2004":"9",
			   "2005":"10","2006":"11","2007":"12","2008":"13","2009":"14","2010":"15","2011":"16","2012":"17","2013":"18","2014":"19","2015":"20","2016":"21"}
	year = yearDict[year]
	#for page in range(0,1):
	for page in range(0, int(nTimes)/50):
		try:
			if page == 0:
				driver.find_element_by_xpath("//select[@id='ctl68_ddNamedDateRange']/option[@value="+year+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddDistance']/option[@value="+distance+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddStroke']/option[@value="+str(stroke)+"]").click()
				driver.find_element_by_xpath("//select[@id='ctl68_ucDistStrokeCourse_ddCourse']/option[@value="+str(course)+"]").click()
				driver.find_element_by_xpath("//input[@id='ctl68_"+sex+"']").click()
				driver.find_element_by_xpath("//input[@id='ctl68_radlStandard_14']").click()
				driver.find_element_by_xpath("//input[@id='ctl68_"+bestAll+"']").click()
				driver.find_element_by_id("ctl68_txtMaxResults").clear()
				driver.find_element_by_id("ctl68_txtMaxResults").send_keys(nTimes)
				if minAge!="All":
					driver.find_element_by_xpath("//select[@id='ctl68_ddAgeStart']/option[@value="+minAge+"]").click()
				if maxAge!="All":
					driver.find_element_by_xpath("//select[@id='ctl68_ddAgeEnd']/option[@value="+maxAge+"]").click()
				driver.find_element_by_id("ctl68_btnSearch").click()

			if page > 0:
				try:
					driver.find_element_by_link_text(str(page+1)).click()
				except WebDriverException:
					#print '//a[@href="javascript:__doPostBack(\'ctl00$ctl63$dgSearchResults$ctl54$ct'+str(100+page)+'\',\'\')"]'
					#driver.find_element_by_xpath('//a[@href="javascript:__doPostBack(\'ctl00$ctl63$dgSearchResults$ctl54$ct'+str(100+page)+'\',\'\')"]').click()
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
		with open('testhtml'+'.txt','w') as ile:
			ile.write(r.encode('utf-8'))
		place=r.find('<td>Meet Results</td>')+25
		end=r.find('</table>',place+1000)
		count=0
		previousResult=""
		#there are vastly more efficient ways to loop through this, but this code is done and works, so I don't care
		while place>0:
			place=r.find('</td>',place+1,end)
			count=(count+1) % 12
			if count==1:
				#print r[place:place+50]
				timeMMSS=r[r.find('>',place+5)+1:r.find('<',place+9)]
				#print "time"+timeMMSS
			if count==4:
				place=r.find('<span',place+1,end)
				swimmer=r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count==8:
				team=r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count==6:
				age=r[r.find('>',place+5)+1:r.find('<',place+9)]
			if count==5:
				fore=r[r.find('>',place+5)+1:r.find('<',place+9)]
				if len(fore)==0:
					foreign=""
				else:
					foreign=fore
			if count==9:
				place = r.find('<span',place+1,end)
				meet = r[r.find('>',place+5)+1:r.find('<',place+9)-8]
				date = r[r.find('<',place+9)-8:r.find('<',place+9)]
				#the web page sometimes returns the same result a bunch of times in a row. this throws a time out if it repeats the swimmer name age time and date of the row above. also throws out the header row
				if timeMMSS=='Time' or previousResult==swimmer+age+timeMMSS+date:
					continue
				previousResult = swimmer+age+timeMMSS+date
				outputstring = meet+'\t'+swimmer+'\t'+age+'\t'+team+'\t'+genderOut+'\t'+event+'\t'+str(toTime(
					timeMMSS))+'\t'+timeMMSS+'\t'+date+'\t'+'\n'
				outputstring = unidecode(outputstring)
				outputstring = str(outputstring).translate(None,"#")
				#print outputstring
				#print "foreign"+foreign
				File.write(outputstring.replace("'", ""))


if __name__ == "__main__":
	driver = init_driver()
	years = ['2011']  # ['2013', '2012']
	genders = ['M', 'F']
	events = ['1500 Free', '400 Free', '200 Free', '100 Free', '50 Free', '100 Fly', '200 Fly', '100 Back', '200 Back',
			'100 Breast', '200 Breast', '200 IM', '400 IM']
	#events = ['200 Back']

	for gender in genders:
		for event in events:
			for year in years:
				course = 'LCM'
				filename = 'Club_' + year + course + gender + event
				print filename
				with open(filename, 'w') as meetFile:
					lookup(driver, event=event, course="LCM", gender=gender, year=year, File=meetFile)
	time.sleep(5)
	driver.quit()