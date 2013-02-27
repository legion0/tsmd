import os
import time

def main():
	f = open("lastBatch.txt", 'r')
	for line in f:
		os.startfile(line)
		time.sleep(10)
	f.close()

if __name__=="__main__":
   main()
