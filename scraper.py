import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
#import crawler.datastore as data
from crawler.datastore import DataStore
import utils.team_utils as tutils
from urllib.robotparser import RobotFileParser
import redis
#import Levenshtein
import requests
import hashlib

r = redis.Redis(host="localhost",port=6379,db=0, decode_responses=True)
# Not sure if we should have this. From a yt vid I watched
# https://www.youtube.com/watch?v=dlI-xpQxcuE

visitedURL="urls"
uniqueUrl = "unique"
blackList = "blackListed"
robotsCheck ="robotsDict"
# check if got seeds once
storeSeeds = 0
repeatedUrl = ['url',0]#If we visit the same url 3 times in a row, add it to blacklist and skip.

def scraper(url, resp, config, logger):
    global storeSeeds
    # getting the seeds
    if storeSeeds == 0:#Store seed robot.txts only once.
        # passes config and logger for method download
        tutils.robotsTxtParseSeeds(config, logger)
        storeSeeds += 1
        # retrieve links from website
    links = extract_next_links(url, resp, config, logger)
    if(links != None):
        return links
    else:
        return list()

def extract_next_links(url, resp, config, logger):
    listLinks = list()

    # removes any fragments
    url = tutils.removeFragment(url)


    if(resp.raw_response == None):  #600+ statuses return a None object for resp.raw_response
        r.sadd(blackList, url)
        return

    if (resp.raw_response.status_code > 399): # ignore all 400-600 errors
        r.sadd(blackList,url)
        return  #maybe add to blacklist instead of returning

    if (resp.status > 399): # ignore all 400-600 errors
        r.sadd(blackList,url)
        return  #maybe add to blacklist instead of returning

    if (resp.raw_response.status_code < 199 and resp.raw_response.status_code < 400):
        if (int(resp.raw_response.headers._store["content-length"][1]) > 100000): #100KB limit
            r.sadd(blackList,url)
            return
        elif (int(resp.raw_response.headers._store["content-length"][1]) < 500): #500 bytes
            r.sadd(blackList,url)
            return
    # make sure url doesent contain types like pdf, mv4 ...
    if (resp.raw_response.status_code < 199 and resp.raw_response.status_code < 400):
        if "text" not in (resp.raw_response.headers._store["content-type"]):
            r.sadd(blackList, url)
            return
    # check if url is valid
    if tutils.isValid(url):
        r.sadd(visitedURL,url)
        r.sadd(uniqueUrl, url)

    # initialize object and pass in html
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

    # removes comments from text
    for tag in soup(text=lambda text: isinstance(text,Comment)):
        tag.extract()

    # removes javascript and css from text
    for element in soup.findAll(['script', 'style']):
        element.extract()


    # increment counter for Domain based on subdomain
    tutils.incrementSubDomain(url)

    # add all tokens found from html response with tags removed
    varTemp = soup.get_text()


    # prevent scraping current page if hash is identical to another page
    if(tutils.isSameHash(varTemp)):
        r.sadd(blackList, url)
        return
    else:
        hashOut = hashlib.md5(varTemp.encode('utf-8')).hexdigest()
        r.sadd(tutils.HASH_SAME, hashOut)   #add hash of text output to redis set


    tutils.tokenize(url, varTemp)

    # look for all links on the current page
    for link in soup.find_all('a'):
        # get absolute urls here before adding to listLInks()
        childURL = link.get('href')

        newlink = ""
        # REGEX function HERE to sanitize url and/or urljoin path to hostname
        if(childURL != None):
            newlink = tutils.returnFullURL(url, childURL)

        if not tutils.isValid(newlink): #skip invalid urls
            r.sadd(blackList, newlink)
            continue

        if(len(newlink) > 0):
            newlink = tutils.removeFragment(newlink)

        ### CHECK IF WE'VE already seen url and skip it ###
        boolSeenBefore = r.sismember(visitedURL, newlink)
        if(boolSeenBefore):
            continue

        if(len(url) > 0):
            listLinks.append(newlink)

        # check if we already have robot.txt domain/sub of current page. if not grab it
        if tutils.getSubDomain(newlink) not in DataStore.robotsCheck or tutils.getDomain(newlink) not in DataStore.robotsCheck:
            tutils.robotsTxtParse(newlink, config, logger)

    return listLinks    #returns the urls to the Frontier object

