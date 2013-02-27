from datetime import datetime
from urlparse import urlparse
import time
import os
import urllib2
import urllib
import re
import json

import engines

import sys, string
import socket

from RotatingLog import RotatingLog

DEFAULT_ENGINE = 'thepiratebay'
DEFAULT_SETTINGS = {
	"engine": "thepiratebay",
	"sleep": 3 * 60
}

scriptPath = ' '.join(str(engines).split()[3:])[1:-2]
DIR_SCRIPT = os.path.dirname(scriptPath)
DIR_TORRENTS = DIR_SCRIPT + os.sep + 'torrents'
DIR_MOVIES = DIR_TORRENTS + os.sep + 'movies'
LOGS_DIR = DIR_SCRIPT + os.sep + 'logs'
LINK_LOGS_DIR = DIR_SCRIPT + os.sep + 'linkLogs'
FILE_SETTINGS = DIR_SCRIPT + os.sep + 'settings.json'

logger = RotatingLog(LOGS_DIR)
linkLogger = RotatingLog(LINK_LOGS_DIR)

settingsObj = None
settings = DEFAULT_SETTINGS

def main(args):
	global settingsObj, settings
	if not os.path.exists(DIR_TORRENTS):
		os.mkdir(DIR_TORRENTS)
	if not os.path.isdir(DIR_TORRENTS):
		print 'please delete file named ' + DIR_TORRENTS
		exit()
	if not os.path.exists(DIR_MOVIES):
		os.mkdir(DIR_MOVIES)
	if not os.path.isdir(DIR_MOVIES):
		print 'please delete file named ' + DIR_MOVIES
		exit()
	
	while True:
		log("Loading settings.json")
		if loadSettings():
			log("Runing")
			for movie in settingsObj['movies']:
				movie.update({k:v for k,v in settingsObj['default']['movie'].iteritems() if k not in movie})
				movie['attempts'] = 2
				while movie['attempts'] > 0:
					movie['attempts'] = movie['attempts'] - 1
					try:
						doMovie(movie)
					except urllib2.URLError as ex:
						log(movie['title'] + ": " + str(ex))
					except socket.error as ex:
						log(movie['title'] + ": " + str(ex))
			
			for show in settingsObj['shows']:
				show.update({k:v for k,v in settingsObj['default']['show'].iteritems() if k not in show})
				show['attempts'] = 2
				while show['attempts'] > 0:
					show['attempts'] = show['attempts'] - 1
					try:
						doShow(show)
					except urllib2.URLError as ex:
						log(show['title'] + ": " + str(ex))
					except socket.error as ex:
						log(show['title'] + ": " + str(ex))
			log("sleeping for: " + str(settings["sleep"]) + ' seconds.')
			time.sleep(settings["sleep"])
		else:
			log("Please fix your settings file, retry in 1 Minute.")
			time.sleep(60)

def loadSettings():
	global settingsObj, settings
	if not os.path.exists(FILE_SETTINGS):
		log('no settings file ' + FILE_SETTINGS)
		return False
	f = open(FILE_SETTINGS, 'r')
	jsonStr = f.read()
	f.close()
	try:
		settingsObj = json.loads(jsonStr)
	except ValueError:
		log("Error Parsing settings.json")
		return False
	if 'default' not in settingsObj:
		settingsObj['default'] = {}
	if 'show' not in settingsObj['default']:
		settingsObj['default']['show'] = {}
	if 'movie' not in settingsObj['default']:
		settingsObj['default']['movie'] = {}
	if 'settings' in settingsObj:
		settings.update(settingsObj["settings"])
	settings["sleep"] = int(settings["sleep"]) * 60
	return True

def doShow(show):
	global settings
	log("Show: " + show['title'])
	folder = DIR_TORRENTS + os.sep + show['title']
	if not os.path.exists(folder):
		os.makedirs(folder)
	engine = settings["engine"]
	if 'engine' in show:
		engine = show['engine']
	if engine not in dir(engines):
		log('no such engine: ' + engine + '. Skipping show.')
		return
	engine = getattr(engines, engine)
	
	showMinSeed = 0
	if 'seeds' in show:
		showMinSeed = int(show['seeds'])
	
	episodesFileName = folder + os.sep + 'episodes.txt'
	if not os.path.exists(episodesFileName):
		f = open(episodesFileName, 'w')
		f.close()
	f = open(episodesFileName, 'r')
	eps = f.read()
	f.close()
	maxEp = getMaxEpisode(re.split('\n', eps)[0:-1])
	#print maxEp
	
	url = engine.constructURL(show)
	htmlFileName = folder + os.sep + 'lastFetch.html'
	response = urllib2.urlopen(url, None, 60)
	show['attempts'] = 0
	html = response.read()
	response.close()
	f = open(htmlFileName, 'w')
	f.write(html)
	f.close()
	
	items = engine.getItems(html)
	
	for itemObj in items:
		
		#print itemObj
		
		if ('title' not in itemObj) or ('link' not in itemObj) or (('seeds' in itemObj) and (itemObj['seeds'] < showMinSeed)):
			continue
		
		if ('user' in show) and ('user' in itemObj) and (show['user'] <> itemObj['user']):
			continue
		
		if not ('season' in itemObj and 'episode' in itemObj):
			continue
		
		#print itemObj['season'], itemObj['episode']
		
		episode = int(itemObj['season'] + itemObj['episode'])
		if episode < maxEp:
			continue
		
		f = open(episodesFileName, 'r')
		eps = f.read()
		f.close()
		seen = re.findall('^' + str(episode) + '$', eps, re.MULTILINE)#need to add "PROPER"
		if len(seen) > 0:
			continue
		
		goodTitle, rule = titleOK(show, itemObj['title'])
		if not goodTitle:
			log("deny: " + itemObj['title'] + ". rule: " + rule)
			continue
		
		log('new episode: ' + str(episode))
		
		logLink(itemObj['link'])
		
		#filePath = folder + os.sep + os.path.split(itemObj['link'])[-1]
		filePath = folder + os.sep + cleanTitle(itemObj['title'])
		
		#urllib.urlretrieve(itemObj['link'], filePath)
		
		#os.startfile(filePath)
		os.startfile(itemObj['link'])
		
		f = open(episodesFileName, 'a')
		f.write(str(episode) + '\n')
		f.close()

def doMovie(movie):
	global settings
	folder = DIR_MOVIES + os.sep + movie['title']
	if not os.path.exists(folder):
		os.makedirs(folder)
	engine = settings["engine"]
	if 'engine' in movie:
		engine = movie['engine']
	if engine not in dir(engines):
		log('no such engine: ' + engine + '. Skipping movie.')
		return
	engine = getattr(engines, engine)
	
	movieMinSeed = 0
	if 'seeds' in movie:
		movieMinSeed = int(movie['seeds'])
	
	movieMinSize = 0
	if 'size>' in movie:
		movieMinSize = int(movie['size>'])
	
	maxItems = 1
	if 'maxItems' in movie:
		maxItems = int(movie['maxItems'])
	
	dlFilePath = folder + os.sep + 'downloaded.txt'
	if not os.path.exists(dlFilePath):
		f = open(dlFilePath, 'w')
		f.close()
	f = open(dlFilePath, 'r')
	dlStrList = f.read()
	f.close()
	dlList = re.split('\n', dlStrList)[0:-1]
	
	if len(dlList) >= maxItems:
		return
	
	log("Movie: " + movie['title'])
	
	if 'url' in movie:
		url = movie['url']
	else:
		url = engine.constructURL(movie)
	htmlFileName = folder + os.sep + 'lastFetch.html'
	
	response = urllib2.urlopen(url, None, 60)
	movie['attempts'] = 0
	html = response.read()
	response.close()
	f = open(htmlFileName, 'w')
	f.write(html)
	f.close()
	
	# f = open(htmlFileName, 'r')
	# html = f.read()
	# f.close()
	
	items = engine.getItems(html)
	
	for itemObj in items:
		if ('title' not in itemObj) or ('link' not in itemObj) or (('seeds' in itemObj) and (itemObj['seeds'] < movieMinSeed)):
			continue
		
		if ('user' in movie) and ('user' in itemObj) and (movie['user'] <> itemObj['user']):
			continue
		
		if 'season' in itemObj or 'episode' in itemObj:
			continue
		
		if ('size>' in movie) and (itemObj['size'] < movieMinSize):
			continue
		
		f = open(dlFilePath, 'r')
		dlStrList = f.read()
		f.close()
		dlList = re.split('\n', dlStrList)[0:-1]
		if len(dlList) >= maxItems:
			break
		
		title = itemObj['title']
		cTitle = cleanTitle(itemObj['title'])
		#fileName = os.path.split(itemObj['link'])[-1]
		if title in dlList:
			continue
		
		goodTitle, rule = titleOK(movie, title)
		if not goodTitle:
			log("deny: " + title + ". rule: " + rule)
			continue
		
		log('new movie: ' + str(cTitle))
		logLink(itemObj['link'])
		
		#filePath = folder + os.sep + fileName
		
		#urllib.urlretrieve(itemObj['link'], filePath)
		
		#os.startfile(filePath)
		os.startfile(itemObj['link'])
		
		f = open(dlFilePath, 'a')
		f.write(title + '\n')
		f.close()

def titleOK(show, title):
	title = cleanTitle(title).lower()
	titleTokens = title.split()
	titleTokens = set(titleTokens)
	if 'deny' in show:
		rules = show['deny']
		if rules is str:
			rules = [rules]
		rules = [x.lower() for x in rules]
		for rule in rules:
			if title.find(rule) != -1:
				return False, rule
	if 'notInTitle' in show:
		rules = show['notInTitle']
		if rules is str:
			rules = [rules]
		rules = set([x.lower() for x in rules])
		res = rules & titleTokens
		if len(res) > 0:
			return False, res.pop()
	if 'inTitle' in show:
		rules = show['inTitle']
		if rules is str:
			rules = [rules]
		rules = set([x.lower() for x in rules])
		res = rules - titleTokens
		if len(res) > 0:
			return False, res.pop()
	return True, None

def cleanTitle(title):
	cTitle = re.sub(r"[^A-Za-z0-9]+", " ", title).strip()
#	print "@", cTitle, "@"
	return cTitle

def getMaxEpisode(episodes):
	maxEp = 0
	for ep in episodes:
		ep = int(ep)
		maxEp = max(ep, maxEp)
	return maxEp
	
def getTimeStr():
	return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def log(entry):
	global logger
	s = getTimeStr() + ": " + entry
	print s
	logger.log(s)

def logLink(link):
	global linkLogger
	linkLogger.log(link)

def logAndExit(entry, exitcode = 1, waittime = 0):
	log(entry)
	if waittime > 0:
		time.sleep(waittime)
	exit(exitcode)

if __name__=="__main__":
	try:
		main(sys.argv[1:])
	except Exception as ex:
		logAndExit(str(ex), waittime = 1)
