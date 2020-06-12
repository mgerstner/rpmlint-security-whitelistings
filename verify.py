#!/usr/bin/python3

import os, sys
import subprocess
import glob
import json
import urllib.request
import tempfile

def printerr(*args, **kwargs):

	kwargs["file"] = sys.stderr

	print(*args, **kwargs)

def checkJSONFile(path):

	with open(path, 'rb') as json_fd:
		try:

			print("Checking", path, "... ", end = '')
			sys.stdout.flush()

			res = subprocess.call(
				["json_verify"],
				close_fds = True,
				shell = False,
				stdin = json_fd
			)

			if res == 0:
				return True
			else:
				print(path, "is not valid JSON!")
				return False

		except FileNotFoundError:

			printerr("Couldn't find json_verify. You need to install yajl (yet-another-json-lib).")
			sys.exit(2)

def checkDuplicateEntries(path):

	# the JSON spec does allow for duplicate dictionary key entries to
	# appear. And the python json parser acts in some (undefined) way in
	# this situation, no error is raised.
	#
	# therefore hook into the parser to detect duplicate keys and error
	# out in this case

	errors = []

	def check_duplicates(ordered_pairs):

		seen = set()

		for k, _ in ordered_pairs:
			if k in seen:
				# don't raise an exception right away we want
				# to collect all duplicates not just the first
				# one
				errors.append(
					"duplicate dictionary key in {} encountered: {}".format(path, k)
				)
			else:
				seen.add(k)

		return ordered_pairs

	with open(path, 'rb') as json_fd:

		data = json.load(json_fd, object_pairs_hook = check_duplicates)

	for error in errors:
		printerr(error)

	return len(errors) == 0

whitelisting = None

def fetchWhitelistingModule():
	whitelisting_module_url = "https://raw.githubusercontent.com/openSUSE/rpmlint-checks/master/Whitelisting.py"

	# only available from python3.5 and newer
	import importlib.util

	with tempfile.NamedTemporaryFile(suffix = ".py") as temp:
		req = urllib.request.urlopen(whitelisting_module_url)
		temp.write(req.read())
		temp.flush()

		spec = importlib.util.spec_from_file_location("Whitelisting", temp.name)
		whitelisting = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(whitelisting)
		return whitelisting


def checkParsing(path):

	global whitelisting
	if not whitelisting:
		whitelisting = fetchWhitelistingModule()

	parser = whitelisting.WhitelistParser(path)

	try:
		entries = parser.parse()
		return True
	except Exception as e:
		printerr(e)
		return False

our_dir = os.path.dirname(os.path.realpath(__file__))
pathspec = os.path.join( our_dir, "*.json" )
res = 0

for json_file in glob.glob(pathspec):

	if not checkJSONFile(json_file):
		res = 1

	if not checkDuplicateEntries(json_file):
		res = 1

	if not checkParsing(json_file):
		res = 1

sys.exit(res)
