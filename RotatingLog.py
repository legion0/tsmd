import datetime
import os, sys, time, json

class RotatingLog:

	class INTERVAL:
		DAY = 2
		HOUR = 3
		MINUTE = 4

		@classmethod
		def toString(cls, val):
			for k,v in vars(cls).iteritems():
				if v == val:
					return k

		@classmethod
		def fromString(cls, str):
			return getattr(cls, str.upper(), None)

	DEFAULT_SETTINGS = {'INTERVAL': 'DAY', 'HISTORY': 30}
	LOG_PREFIX = 'log_'
	LOG_SUFFIX = '.txt'

	def __init__(self, logDirectory = 'logs'):
		self.logDirectory = logDirectory
		if not os.path.exists(self.logDirectory):
			os.makedirs(self.logDirectory)
		self.settingsFile = self.logDirectory + os.sep + 'settings.json.js'
		self.__loadSettings()
		self.__cleanUp()

	def log(self, entry):
		self.write(entry + '\n')

	def write(self, entry):
		filePath = self.__getCurrentFilePath()
		f = open(filePath, 'a')
		f.write(entry)
		f.close()
		self.__cleanUp()

	def __getCurrentFilePath(self):
		now = datetime.datetime.now().timetuple()
		filePath = self.logDirectory + os.sep + RotatingLog.LOG_PREFIX + str(now[0]).rjust(4,'0')
		for i in range(1,self.interval+1):
			filePath += str(now[i]).rjust(2,'0')
		filePath += '.txt'
		return filePath

	def __loadSettings(self):
		if os.path.exists(self.settingsFile):
			f = open(self.settingsFile, 'r')
			jsonStr = f.read()
			f.close()
			self.settings = json.loads(jsonStr)
		else:
			self.settings = RotatingLog.DEFAULT_SETTINGS

		self.interval = RotatingLog.INTERVAL.fromString(self.settings['INTERVAL'])
		self.timeDelta = datetime.timedelta(days=30)
		if self.interval == RotatingLog.INTERVAL.DAY:
			self.timeDelta = datetime.timedelta(days=self.settings['HISTORY'])
			self.cleanUpInterval = datetime.timedelta(days=1)
		elif self.interval == RotatingLog.INTERVAL.HOUR:
			self.timeDelta = datetime.timedelta(hours=self.settings['HISTORY'])
			self.cleanUpInterval = datetime.timedelta(hours=1)
		elif self.interval == RotatingLog.INTERVAL.MINUTE:
			self.timeDelta = datetime.timedelta(minutes=self.settings['HISTORY'])
			self.cleanUpInterval = datetime.timedelta(minutes=1)
		self.lastCleanUp = datetime.datetime.now() - self.cleanUpInterval

	def __saveSettings(self):
		f = open(self.settingsFile, 'w')
		f.write(json.dumps(self.settings, sort_keys=True, indent=4, separators=(',', ': ')))
		f.close()

	def __cleanUp(self):
		needsCleaning = datetime.datetime.now() - self.lastCleanUp >= self.cleanUpInterval
		if not needsCleaning:
			return
		_, currentLogFileName = os.path.split(self.__getCurrentFilePath())
		for f in os.listdir(self.logDirectory):
			if (f.startswith(RotatingLog.LOG_PREFIX)):
				if not self.__compareLogs(currentLogFileName, f):
					os.remove(self.logDirectory + os.sep + f)
		self.lastCleanUp = datetime.datetime.now()

	def __compareLogs(self, file1, file2):
		file1 = file1[len(RotatingLog.LOG_PREFIX):-len(RotatingLog.LOG_SUFFIX)]
		file2 = file2[len(RotatingLog.LOG_PREFIX):-len(RotatingLog.LOG_SUFFIX)]
		dt1 = RotatingLog.stamp2Datetime(file1)
		dt2 = RotatingLog.stamp2Datetime(file2)
		return dt2 - dt1 >= - self.timeDelta

	@staticmethod
	def stamp2Datetime(stamp):
		arr = [int(stamp[0:4])]
		for i in xrange(4,len(stamp),2):
			arr.append(int(stamp[i:i+2]))
		for i in xrange(len(arr),3):
			arr.append(1)
		for i in xrange(len(arr),6):
			arr.append(0)
		return datetime.datetime(*arr)
