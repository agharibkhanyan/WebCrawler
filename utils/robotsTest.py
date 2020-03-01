from crawler.datastore import DataStore
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import re
from urllib.parse import urljoin
from utils import normalize, get_urlhash
import redis
import tldextract
import json
import utils.reportUtil as report
from utils.cacheRobotParser import CacheRobotFileParser

def getSubDomain(url):
    ext = tldextract.extract(str(url))
    domainUrl = ''
    if ext.subdomain == '':  # Returns url with subdomain attached.
        return f"{ext.domain}.{ext.suffix}"#'.'.join([ext.domain, ext.suffix])
    #domainUrl = '.'.join(ext[:2])
    domainUrl = f"{ext.subdomain}.{ext.domain}.{ext.suffix}"#'.'.join([domainUrl, ext.suffix])

    return domainUrl

def getDomain(url):
    # Gets the domain or subdomain of a url and returns it.
    ext = tldextract.extract(url)
    #domainUrl = ext.domain
    domainUrl = f"{ext.domain}.{ext.suffix}"#'.'.join([domainUrl, ext.suffix])

def robotsTxtParse(url, config, logger):
    # Finds the robot.txt of a domain and subdomain(if one exists) and
    # Stores it in DataStore.RobotChecks
    scheme = urlparse(url).scheme #scheme needed to read robots.txt

    domain = getDomain(url)
    #val=r.hget(robotsCheck,"bhh").decode('utf-8')
    if domain != '' and domain not in DataStore.robotsCheck:
    #if domain != '' and domain not in r.hexists(robotsCheck, domain):
        robotTxtUrl = f"{scheme}://{domain}/robots.txt"
        robot = RobotFileParser(config, logger)
        robot.set_url(robotTxtUrl)
        robot.read()
        #r.hset(robotsCheck, domain, robot)
        DataStore.robotsCheck[domain] = robot

    subdomain = getSubDomain(url)
    if subdomain != '' and subdomain not in DataStore.robotsCheck:
    #if subdomain != '' and not r.hexists(robotsCheck,subdomain):
        robotTxtUrl = f"{scheme}://{subdomain}/robots.txt"
        robot = RobotFileParser(config, logger)
        robot.set_url(robotTxtUrl)
        robot.read()
        #r.hset(robotsCheck, subdomain, robot)
        DataStore.robotsCheck[subdomain] = robot

def robotsTxtParseSeeds():
    # Stores the robot.txt of the seed urls in DataStore.RobotChecks
    seedUrls = ['https://today.uci.edu/department/information_computer_sciences/',
    'https://www.ics.uci.edu',
    'https://www.cs.uci.edu',
    'https://www.informatics.uci.edu',
    'https://www.stat.uci.edu']
    for seedUrl in seedUrls:
        scheme = urlparse(seedUrl).scheme
        domain = getSubDomain(seedUrl)
        robotTxtUrl = f"{scheme}://{domain}/robots.txt"
        robot = RobotFileParser()
        robot.set_url(robotTxtUrl)
        robot.read()
        DataStore.robotsCheck[domain] = robot


def robotsAllowsSite(subdomain, url):
    if subdomain in DataStore.robotsCheck.keys():
    #if r.hexists(robotsCheck,subdomain):
        #robot = r.hget(robotsCheck,subdomain)#.decode('utf-8')
        robot = DataStore.robotsCheck[subdomain]
        return robot.can_fetch("*", url)

    return True


if __name__ == "__main__":
    #reportQuestion3()
    #reportQuestion4()
    robotsTxtParseSeeds()
    boolCanFetch = robotsAllowsSite(getSubDomain("https://today.uci.edu/calendar?event_types%5B%5D=48779"), "https://today.uci.edu/calendar?event_types%5B%5D=48779")
    boolCanFetch22 = robotsAllowsSite(getSubDomain("https://today.uci.edu/calendar/month"), "https://today.uci.edu/calendar/month")
    boolCanFetch33 = robotsAllowsSite(getSubDomain("https://today.uci.edu/search/events?search=game&type="), "https://today.uci.edu/calendar/month")
    print(boolCanFetch)
    print(boolCanFetch22)
    print(boolCanFetch33)
