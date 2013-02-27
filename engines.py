import urllib, re, os

class thepiratebay:
	DEFAULT_CAT = '0'
	DEFAULT_SORT = '99'
	FIND_ITEMS = '<tr>\n\t\t<td class="vertTh">.*?</tr>'
	PARSE_ITEM = 	'<a href="/browse/(\d+)"[^>]+>[^<]+<[^\n]+\n' +\
				'\s+\(<a href="/browse/(\d+)"[^>]+>[^<]+<[^\n]+\n' +\
				'.*?' +\
				'<div class="detName">\s*<a[^>]+>([^<]+)<[^\n]+\n' +\
				'</div>\n' +\
				'\s*<a href="([^"]+)" title="Download this torrent using magnet"[^\n]+\n' +\
				'.*?Size (\d+\.?\d*)&nbsp;([^,]+).*?<a[^>]+>([^<]+)<[^\n]+\n' +\
				'.*?' +\
				'\s+<td[^>]+>(\d+)<[^\n]+\n' +\
				'\s+<td[^>]+>(\d+)<[^\n]+\n'
	
	@staticmethod
	def constructURL(show):
		escapedTitle = urllib.quote(show['title'])
		cat = thepiratebay.DEFAULT_CAT
		if 'cat' in show:
			cat = show['cat']
		sort = thepiratebay.DEFAULT_SORT
		if 'sort' in show:
			sort = show['sort']
		page = '0'
		return 'http://thepiratebay.se/search/' + escapedTitle + '/' + str(page) + '/' + str(sort) + '/' + str(cat)
	
	@staticmethod
	def getItems(html):
		# print html
		itemsHtml = re.findall(thepiratebay.FIND_ITEMS, html, re.DOTALL)
		items = []
		for itemHtml in itemsHtml:
			itemArr = re.findall(thepiratebay.PARSE_ITEM, itemHtml, re.DOTALL)
			if len(itemArr) < 1:
				continue
			itemArr = itemArr[0]
			itemObj = {'cat~': itemArr[0], 'cat': itemArr[1], 'title': itemArr[2], 'link': itemArr[3], 'size':float(itemArr[4]), 'sizeUnits':itemArr[5], 'user':itemArr[6], 'seeds': itemArr[7], 'leechers': itemArr[8]}
			if itemObj['sizeUnits'] == 'GiB':
				itemObj['size'] *= 1024
			itemObj.pop('sizeUnits', 0)
			episodeTup = re.findall('S(\d+)E(\d+)', itemObj['title'])
			if len(episodeTup) == 1 and len(episodeTup[0]) == 2:
				itemObj['season'] = episodeTup[0][0]
				itemObj['episode'] = episodeTup[0][1]
			items.append(itemObj)
		return items