#!/usr/bin/env python2
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

import hashlib

from RotatingLog import RotatingLog
from copy import deepcopy

APP_SAFE_NAME = "web2rss"

SETTINGS_DIR = os.path.expanduser(os.path.join("~", ".config", APP_SAFE_NAME))
LOGS_DIR = os.path.join(SETTINGS_DIR, "logs")
FILE_SETTINGS = os.path.join(SETTINGS_DIR, "settings.js")
FILE_HISTORY = os.path.join(SETTINGS_DIR, "history.js")

logger = None

settings = {}
history = {}

def main(args):
	check_first_run()
	init_logger()
	while True:
		log_info("Loading settings")
		if load_settings():
			log_info("Runing")
			for item in settings['movies']:
				item = merge_dicts(settings['movie_defaults'], item)
				item["type"] = "movie"
				do_item(item)
			for item in settings['shows']:
				item = merge_dicts(settings['show_defaults'], item)
				item["type"] = "show"
				do_item(item)
			save_history()
			sleep_duration = settings["settings"]["sleep"]
			log_info("sleeping for: %r Minutes." % sleep_duration)
			do_sleep(sleep_duration*60)
		else:
			log_error("Please fix your settings file, retry in 1 Minute.")
			do_sleep(60)
			time.sleep(0.5) # let user escape sleep loop

def check_first_run():
	if not os.path.exists(FILE_SETTINGS):
		os.makedirs(SETTINGS_DIR)
		os.makedirs(LOGS_DIR)
		with open(FILE_SETTINGS, "w") as f:
			f.write(pretty_json(DEFAULT_SETTINGS))
		with open(FILE_HISTORY, "w") as f:
			f.write(pretty_json(DEFAULT_HISTORY))

def init_logger():
	global logger
	logger = RotatingLog(LOGS_DIR)

def load_settings():
	global settings, history
	if not os.path.exists(FILE_SETTINGS):
		log_error('no settings file: %r ' % FILE_SETTINGS)
		return False
	with open(FILE_SETTINGS) as f:
		jsonStr = f.read()
	try:
		settings = json.loads(jsonStr)
	except ValueError as ex:
		log_error("Error Parsing settings.json")
		log_error(str(ex))
		return False
	if os.path.exists(FILE_HISTORY):
		with open(FILE_HISTORY) as f:
			history = json.loads(f.read())
	return True

def save_history():
	update_show_last_seen()
	history_string = pretty_json(history)
	with open(FILE_HISTORY, "w") as f:
		f.write(history_string)

def do_sleep(duration):
	try:
		time.sleep(duration)
	except KeyboardInterrupt:
		pass

def merge_dicts(a, b):
	result = deepcopy(a)
	for key, value in b.viewitems():
		if isinstance(value, dict):
			old_value = result.get(key)
			if not isinstance(old_value, dict):
				old_value = {}
			result[key] = merge_dicts(old_value, value)
#		elif isinstance(value, list):
#			old_value = result.get(key)
#			if not isinstance(old_value, list):
#				old_value = []
#			result[key] = old_value + deepcopy(value)
		else:
			result[key] = deepcopy(value)
	return result

def do_item(item):
	item_type = item["type"]
	if item_type == "movie" and is_movie_downloaded(item):
		return False
	attempts = item.get("attempts", 1)
	while attempts > 0:
		try:
			log_info("%s: %s" %(item["type"].capitalize(), item['title']))
			engine = get_engine(item)
			if engine is None:
				break
			url = engine.constructURL(item)
			timeout = settings.get("url_timeout", 10)
			response = urllib2.urlopen(url, None, timeout)
			item['attempts'] = 0 # we succeded to get the web page
			html = response.read()
			response.close()
			items = engine.getItems(html)
			for remote_item in items:
				if item_type == "movie" and is_movie_downloaded(item):
					return False
				if not item_is_ok(item, remote_item):
					continue
				if item_type == "show":
					current_episode = get_remote_episode(remote_item)
					current_episode_str = episode_to_str(current_episode)
					current_episode_int = episode_to_int(current_episode)
					log_info('Downloading episode: %s.' % (current_episode_str,))
					set_show_seen_episode(item, current_episode_int)
				elif item_type == "movie":
					log_info('Downloading movie: %r.' % (remote_item["title"],))
					set_movie_downloaded(item)
				link = remote_item['link']
				if link.startswith("magnet:"):
					open_magnet_link(item, remote_item)
				elif link.endswith(".torrent"):
					open_torrent_link(item, remote_item)
				if item_type == "movie":
					return True
		except urllib2.URLError as ex:
			log_error(item['title'] + ": " + str(ex))
		except socket.error as ex:
			log_error(item['title'] + ": " + str(ex))
		attempts -= 1
	return attempts > 0

def item_is_ok(item, remote_item):
	if item["type"] == "movie" and is_movie_downloaded(item):
		return False
	min_seeds = int(item.get("seeds", 0))
	if min_seeds > 0 and remote_item['seeds'] < min_seeds:
		return False
	user_name = item.get("user", "")
	if user_name != "" and item['user'] != remote_item['user']:
		return False
	min_size = int(item.get("min_size", 0))
	if min_size > 0 and remote_item['size'] < min_size:
		return False
	good_title, rule = title_is_ok(item, remote_item['title'])
	if not good_title:
		if rule is not None:
			log_verbose("denied: %r based on rule %r." % (remote_item['title'], rule))
		else:
			log_debug("denied: %r." % (remote_item['title'],))
		return False
	if item["type"] == "show":
		if not ('season' in remote_item and 'episode' in remote_item):
			return False
		current_episode = get_remote_episode_int(remote_item)
		last_seen_episode = get_last_seen_episode(item)
		if is_show_episode_seen_now(item, current_episode) or current_episode <= last_seen_episode:
			return False
	elif item["type"] == "movie":
		pass
	return True

def get_remote_episode(remote_item):
	return (int(remote_item.get("season", 0)), int(remote_item.get("episode", 0)))

def get_remote_episode_int(remote_item):
	return episode_to_int(get_remote_episode(remote_item))

def get_remote_episode_str(remote_item):
	return episode_to_str(get_remote_episode(remote_item))

def episode_to_str(episode):
	return "%02d_%03d" % episode

def episode_to_int(episode):
	return int(episode_to_str(episode).replace("_", ""))

def get_last_seen_episode(item):
	shows_hist = history["show"]
	item_safe_title = safe_file_name(item["title"])
	show_hist = shows_hist.get(item_safe_title, {})
	return show_hist.get("last_seen_episode", 0)

DEFAULT_SHOW_HIST = {"last_seen_episode": 0}
DEFAULT_MOVIE_HIST = {"downloaded": False}

def set_last_seen_episode(show, episode):
	global history
	item_safe_title = safe_file_name(show["title"])
	if not item_safe_title in history["show"]:
		history["show"][item_safe_title] = deepcopy(DEFAULT_SHOW_HIST)
	history["show"][item_safe_title]["last_seen_episode"] = episode

shows_seen_episodes = []
def update_show_last_seen():
	global shows_seen_episodes
	for show in shows_seen_episodes:
		set_last_seen_episode(show, max(show["seen_episodes"]))
	shows_seen_episodes = []

def set_show_seen_episode(show, episode):
	if "seen_episodes" not in show:
		shows_seen_episodes.append(show)
		show["seen_episodes"] = set()
	show["seen_episodes"].add(episode)

def is_show_episode_seen_now(show, episode):
	return episode in show.get("seen_episodes", [])

def is_movie_downloaded(movie):
	item_safe_title = safe_file_name(movie["title"])
	movie_hist = history["movie"].get(item_safe_title, {})
	return movie_hist.get("downloaded", False)

def set_movie_downloaded(movie):
	global history
	item_safe_title = safe_file_name(movie["title"])
	if not item_safe_title in history["movie"]:
		history["movie"][item_safe_title] = deepcopy(DEFAULT_MOVIE_HIST)
	history["movie"][item_safe_title]["downloaded"] = True


def get_engine(item):
	engine = item["engine"]
	if engine not in dir(engines):
		return None
	return getattr(engines, engine)

def open_magnet_link(item, remote_item):
	link = remote_item["link"]
	file_name = generate_autoload_file_name(item, remote_item)
	file_name += ".magnet"
	file_path = os.path.join(item["auto_load_directory"], file_name)
	with open(file_path, "w") as f:
		f.write(link)

def generate_autoload_file_name(item, remote_item):
	file_name = safe_file_name(item["title"])
	if item["type"] == "show":
		file_name += "_%s" % get_remote_episode_str(remote_item)
	file_name += "_%s" % hashlib.sha1(remote_item["link"]).hexdigest()[:8]
	return file_name

#def open_torrent_link(item, link):
#	pass


#filePath = folder + os.sep + os.path.split(remote_item['link'])[-1]
#filePath = folder + os.sep + clean_title(remote_item['title'])
#urllib.urlretrieve(remote_item['link'], filePath)
#os.startfile(filePath)

def title_is_ok(item, title):
	title = clean_title(title).lower()
	showT = clean_title(item["title"]).lower()
	titleList = title.split()
	showTitleList = showT.split()
#	if title.find(showT) == -1:
#		return False, None
	if find_sublist(titleList, showTitleList) == -1:
		return False, None
	titleTokens = set(titleList)
	showTitleTokens = set(showTitleList)
	if not (showTitleTokens <= titleTokens):
		return False, None
	if 'deny' in item:
		rules = item['deny']
		rules = [str(x).lower() for x in rules]
		for rule in rules:
			rule = clean_title(rule).lower()
			if title.find(rule) != -1:
				return False, rule
	if 'not_in_title' in item:
		rules = item['not_in_title']
		rules = set([str(x).lower() for x in rules])
		res = rules & titleTokens
		if len(res) > 0:
			return False, res.pop()
	if 'in_title' in item:
		rules = item['in_title']
		rules = set([str(x).lower() for x in rules])
		res = rules - titleTokens
		if len(res) > 0:
			return False, res.pop()
	return True, None

def find_sublist(list_, sublist):
	if not list_:
		return -1
	if not sublist:
		return 0
	size = len(sublist)
	first = sublist[0]
	if size == 1:
		return list_.index(first)
	pos = -1
	try:
		while True:
			pos = list_.index(first, pos+1)
			if pos == -1:
				return pos
			if list_[pos:pos+size] == sublist:
				return pos
	except ValueError:
		return -1

def safe_file_name(file_name, replace_char = "_"):
	return re.sub(r"[^A-Za-z0-9]+", replace_char, str(file_name)).lower().strip(replace_char)

def clean_title(title):
	return re.sub(r"[^A-Za-z0-9]+", " ", str(title)).strip(" ")

def getMaxEpisode(episodes):
	maxEp = 0
	for ep in episodes:
		ep = int(ep)
		maxEp = max(ep, maxEp)
	return maxEp

def pretty_json(obj, sort_keys=True, indent=4, separators=(',', ': ')):
	return json.dumps(obj, sort_keys=sort_keys, indent=indent, separators=separators)

def get_timestamp_str():
	return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

LOG_FORMAT = "%s | %-10s | %s"

def log_error(entry):
	print >> sys.stderr, entry
	logger.log(format_log_msg(entry, "ERROR"))
def log_warning(entry):
	logger.log(format_log_msg(entry, "WARNING"))
def log_info(entry):
	print entry
	logger.log(format_log_msg(entry, "INFO"))
def log_verbose(entry):
	logger.log(format_log_msg(entry, "VERBOSE"))
def log_debug(entry):
	logger.log(format_log_msg(entry, "DEBUG"))
def format_log_msg(entry, level):
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	return LOG_FORMAT % (timestamp, level, entry)

DEFAULT_SETTINGS = {
	"shows": [
		{"title": "some random show you like to watch"}
	],
	"movies": [
		{"title": "some random movie you are waiting for"}
	],
	"show_defaults": {
		"engine": "thepiratebay",
		"auto_load_directory": "/mnt/downloads/autoload",
		"cat": "208",
		"sort": "7",
		"not_in_title": ["webrip", "webdl"],
		"seeds": 100
	},
	"movie_defaults": {
		"engine": "thepiratebay",
		"auto_load_directory": "/mnt/downloads/auto_load_directory",
		"cat": "207",
		"sort": "7",
		"not_in_title": ["trailer", "cam", "R5", "TS", "dvdscr", "dvd", "BluRaySCR", "DVDScri", "scr", "HDSCR", "HDTV", "HDTS", "webrip", "webdl", "screener", "UPSCALED"],
		"deny": ["web dl"],
		"in_title": ["720P"],
		"size>": 3000,
		"seeds": 200,
		"maxItems": 1
	},
	"settings": {
		"sleep": 360
	}
}

DEFAULT_HISTORY = {
	"show": {},
	"movie": {}
}

if __name__=="__main__":
	main(sys.argv[1:])
