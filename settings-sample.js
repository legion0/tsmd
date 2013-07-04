{
	"shows": [
		{"title": "Spartacus"},
		{"title": "The Walking Dead", "user": "eztv"},
		{"title": "Doctor Who", "deny": ["Doctor Who Confidential", "1080p"]}
	],
	"movies": [
		{"title": "After Earth"},
		{"title": "Green Lantern 2", "not_in_title": ["2011", "trailer", "cam", "R5", "TS", "dvdscr", "dvd", "BluRaySCR", "DVDScri", "scr", "HDSCR", "webrip", "webdl", "screener", "UPSCALED"]},
		{"title": "The Avengers", "url": "http://thepiratebay.se/search/The%20Avengers/0/7/207", "not_in_title": ["2006", "trailer", "cam", "R5", "TS"], "in_title": ["720P"], "size>": 2000, "seeds": 200, "maxItems": 1}
	],
	"show_defaults": {
		"engine": "thepiratebay",
		"auto_load_directory": "E:\\Torrent\\autoload",
		"cat": "208",
		"sort": "7",
		"not_in_title": ["webrip", "webdl"],
		"seeds": 100
	},
	"movie_defaults": {
		"engine": "thepiratebay",
		"auto_load_directory": "E:\\Torrent\\autoload",
		"cat": "207",
		"sort": "7",
		"not_in_title": ["trailer", "cam", "R5", "TS", "dvdscr", "dvd", "BluRaySCR", "DVDScri", "scr", "HDSCR", "HDTV", "HDTS", "webrip", "webdl", "screener", "UPSCALED"],
		"in_title": ["BlueRay", "720P"],
		"deny": ["web dl"],
		"size>": 3000,
		"seeds": 200
	},
	"settings": {
		"sleep": 360,
		"url_timeout": 10
	}
}
