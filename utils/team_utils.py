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

## connect redis to server on a specific port
r = redis.Redis(host="localhost",port=6379,db=0, decode_responses=True)

# dataset names
mostTokensUrl="mostTokens"
setDomainCount = "setDomainCount"
TOKEN_COUNT_NAME = "tokenCount"
TOKEN_COUNT_KEY = "dictKey"
HASH_SAME = "hashSame"
blackList = "blackListed"
visitedURL = "urls"
#ask artur for explaination these are actually pretty useful
four0four = ""


icsDomains = {}#Added to keep track of specifically ics Domains

'''
Finds the domain/subdomain of url gets robots.txt
Stores the domain/subdomain as a key in robotsCheck
I think we just need to call subdomain(url) to get a key, because all urls should have the 5 seeds as their domain.
May remove adding domain to robotchecks part.

Thought process: robots.txt is found in the root page which is usually a domain or subdomain. In order to check if a url is allowed or not, 
just find its domain/subdomain and look at the disallowed section.
'''

def robotsTxtParse(url, config, logger):
    # Finds the robot.txt of a domain and subdomain(if one exists) and
    # Stores it in DataStore.RobotChecks
    # call urlparse to filter the url and seperate the parts
    scheme = urlparse(url).scheme #scheme needed to read robots.txt

    # pass url to get domain
    domain = getDomain(url)
    if domain != '' and domain not in DataStore.robotsCheck and domain != 'uci.edu':
        # get the url of robot.txt
        robotTxtUrl = f"{scheme}://{domain}/robots.txt"
        # retrieve from cache. stix server
        robot = CacheRobotFileParser(config, logger)
        robot.set_url(robotTxtUrl)
        # retrieve user agents and allow/dissalow permissions
        robot.read()
        # store robots.txt according to domain of url
        DataStore.robotsCheck[domain] = robot
    # get subdomain and same as above
    subdomain = getSubDomain(url)
    if subdomain != '' and subdomain not in DataStore.robotsCheck:
        robotTxtUrl = f"{scheme}://{subdomain}/robots.txt"
        robot = CacheRobotFileParser(config, logger)
        robot.set_url(robotTxtUrl)
        robot.read()
        DataStore.robotsCheck[subdomain] = robot

def robotsTxtParseSeeds(config, logger):
    # Stores the robot.txt of the seed urls in DataStore.RobotChecks
    seedUrls = ['https://today.uci.edu/department/information_computer_sciences/',
    'https://www.ics.uci.edu',
    'https://www.cs.uci.edu',
    'https://www.informatics.uci.edu',
    'https://www.stat.uci.edu']
    # retrieve robots.txt from seed urls
    for seedUrl in seedUrls:
        scheme = urlparse(seedUrl).scheme
        domain = getSubDomain(seedUrl)
        robotTxtUrl = f"{scheme}://{domain}/robots.txt"
        robot = CacheRobotFileParser(config, logger)
        robot.set_url(robotTxtUrl)
        robot.read()
        DataStore.robotsCheck[domain] = robot
        #r.hset(robotsCheck, domain, robot)

def robotsAllowsSite(subdomain, url):
    # check if url is allowed or dissalowed according to robot.txt
    if subdomain in DataStore.robotsCheck.keys():
    #if r.hexists(robotsCheck,subdomain):
        #robot = r.hget(robotsCheck,subdomain)#.decode('utf-8')
        robot = DataStore.robotsCheck[subdomain]
        return robot.can_fetch("*", url)

    return True #if robots.txt not found, then we can scrape freely


### CHANGED TO ADD SUFFIX TO DOMAIN
# get domain of url
def getDomain(url):
    # Gets the domain or subdomain of a url and returns it.
    ext = tldextract.extract(url)
    domainUrl = f"{ext.domain}.{ext.suffix}"#'.'.join([domainUrl, ext.suffix])

    return domainUrl

### CHANGED TO ADD SUFFIX TO DOMAIN
# get subdomain
def getSubDomain(url):
    ext = tldextract.extract(str(url))
    domainUrl = ''
    if ext.subdomain == '':  # Returns url with subdomain attached.
        return f"{ext.domain}.{ext.suffix}"#'.'.join([ext.domain, ext.suffix])
    domainUrl = f"{ext.subdomain}.{ext.domain}.{ext.suffix}"#'.'.join([domainUrl, ext.suffix])

    return domainUrl

# append relative path and parent domain to full url
def returnFullURL(parent_url, strInput):
    parsed_uri = urlparse(parent_url)
    result = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)   #remove slash

    if (strInput.strip() == "/"):
        return ""
    if (strInput.strip() == "#"):
        return ""
    if ("#" in strInput.strip() and removeFragment(strInput) == ""):
        return ""
    else:
        return urljoin(result, strInput)

# count subdomains
def incrementSubDomain(strDomain):
    parsed_uri = urlparse(strDomain)
    # get the whole url without the path
    result = '{uri.netloc}'.format(uri=parsed_uri)   #remove slash at end
    result = getSubDomain(result)
    result = result.lower().replace("www.", "")

    #count subdomains
    if r.hexists(setDomainCount,result):
        val = r.hget(setDomainCount,result)
        val = int(val)
        val += 1
        r.hset(setDomainCount,result,val)
    else:
        r.hset(setDomainCount,result,1)

    #r.hset(setDomainCount)
    #DataStore.subDomainCount[result] = DataStore.subDomainCount.get(result, 0) + 1

# tokenizer
def tokenize(url, rawText):
    # take letters/numbers and also keep ' in words like can't
    listTemp = re.split(r"[^a-z0-9']+", rawText.lower())

    #if r.hget(mostTokensUrl, ):
    # count url with most tokens
    if (DataStore.mostTokensUrl[1] < len(listTemp)):
        DataStore.mostTokensUrl[0] = url
        DataStore.mostTokensUrl[1] = len(listTemp)
        # cant find a workaround so im just storing it locally and in the database
        r.delete(mostTokensUrl)
        r.hset(mostTokensUrl,url,len(listTemp))


    ##### STORE word counts in dictionary inside of redis #####
    dictCounter = dict()
    dictTEMP = dict()
    # save token counts inside redis hset using token count key
    # check if dict exists. if not create one
    if not r.hexists(TOKEN_COUNT_NAME, TOKEN_COUNT_KEY):
        r.hset(TOKEN_COUNT_NAME, TOKEN_COUNT_KEY, json.dumps(dictCounter).encode('utf-8'))
        dictCounter = r.hgetall(TOKEN_COUNT_NAME)
    else:
        dictCounter = r.hgetall(TOKEN_COUNT_NAME)
    # get json string from redis and convert to python dict
    dictTEMP = dict(json.loads(dictCounter[TOKEN_COUNT_KEY]))
    # check if dict is valid
    boolOnly = False
    if len(dictTEMP) > 0:
        boolOnly = True
        dictTEMP = dict(json.loads(dictTEMP[TOKEN_COUNT_KEY]))
    # increment count
    for word in listTemp:
        if not word in dictTEMP:
            dictTEMP[word] = 1
        else:
            dictTEMP[word] += 1
    # convert back to json string
    dictCounter[TOKEN_COUNT_KEY] = json.dumps(dictTEMP)

    # save back into redis
    r.hset(TOKEN_COUNT_NAME, TOKEN_COUNT_KEY, json.dumps(dictCounter))

    # if bad url add to blacklist
    if (len(listTemp) == 0):
        r.sadd(blackList,url)

#### ADDED IF STATEMENTS TO CHECK FOR CALENDAR
#if url has been blacklisted before
def isBlackListed(str):
    if r.sismember(blackList,str):
    #if str in DataStore.blackList:
        return True
    return False

### *DO NOT* ADD isSameHash() to isValid() ###
def isSameHash(str):
    if r.sismember(HASH_SAME,str):
        return True
    return False

def removeFragment(str):
    str = str.split('#')[0]
    return str

# ignore comments from forum
def ifConsideredSpam(str):
    try:
        str = str.split('?')[1]
        str = str.split('=')[0]
        if "replytocom" in str:
            return True
    except:
        return False
    return False

def ifInUCIDomain(str):
    if 'today.uci.edu/department/information_computer_sciences' in str:
        return True
    str = getSubDomain(str)
    if '.ics.uci.edu'in str or '/ics.uci.edu' in str:
        return True
    if '.cs.uci.edu' in str or '/cs.uci.edu' in str:
        return True
    if '.informatics.uci.edu' in str or '/informatics.uci.edu' in str:
        return True
    if '.stat.uci.edu' in str or '/stat.uci.edu' in str:
        return True
    return False

def is_validDEFAULT(url):
    try:
        parsed = urlparse(url)
        subdomain = getSubDomain(url)#key = '://'.join([tutils.getSubDomain(url), parsed.scheme])

        if parsed.scheme not in set(["http", "https"]):
            return False

        ### COMMENT BACK IN WHEN FINISHED ###
        if not robotsAllowsSite(subdomain, url):
            return False

        #if url in DataStore.blackList:
        #if r.sismember(visitedURL,url):
            #return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|jpg|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4|rvi"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        return False

#is url valid
def isValid(str):

    if isBlackListed(str):
        return False
    if r.sismember(visitedURL, str):
        return False
    if not is_validDEFAULT(str):
        return False
    if ifConsideredSpam(str):
        return False
    if not ifInUCIDomain(str):
        return False
    if badUrl(str):
        return False
    if ifRepeatPath(str):
        return False
    return True

def badUrl(str):
    if "search" in str:
        return True
    if "calendar" in str:
        return True
    if "graphics" in str:
        return True
    if "color" in str:
        return True
    if "ppt" in str:
        return True
    if "pdf" in str:
        return True
    if len(str)>150:
        return True
    if "login" in str:
        return True
    if "://cbcl" in str:
        return True
    if "www.amazon.com" in str:
        return True
    if "events/category/boothing" in str:
        return True
    if "difftype=sidebyside" in str:
        return True
    if 'https://today.uci.edu/department/information_computer_sciences/calendar' in str:
        return True
    if 'https://www.ics.uci.edu/~eppstein/pix/chron.html' in str:
        return True
    if ".htm" in str:
        return True
    if '.zip' in str:
        return True
    if "gallery" in str:
        return True
    if "signup" in str:
        return True
    if "/event/" in str:
        return True
    if "events/" in str:
        return True
    if "wics-" in str:
        return True
    if "share" in str:
        return True
    if "slides" in str:
        return True
    if ".txt" in str:
        return True
    if 'flamingo.' in str:
        return True
    if 'facebook'in str:
        return True
    if 'twitter' in str:
        return True
    if '//swiki.ics'in str:
        return True
    if 'eppstein/pix' in str:
        return True

    return False

def ifRepeatPath(input):
    origUrl = input
    path = urlparse(input).path.strip()

    arrsplit = path.split("/")
    iCount = 0
    strcurrent = ""
    loopiter = 0

    #check everything after first element
    for itoken in arrsplit:
        # if real url
        if(itoken.strip() == "/"):
            arrsplit = arrsplit[1:]
            continue
        # check if empty string
        if (itoken.strip() == ""):
            arrsplit = arrsplit[1:]
            continue

        strcurrent = arrsplit[0]
        # make array smaller and smaller until true of false
        arrsplit = arrsplit[1:]

        # compare all tokens to very first index
        for second in arrsplit:
            if (second == strcurrent):
                r.sadd(blackList, origUrl)
                return True
    return False
# check if the years are valid
def _tryConvertToInt(str):
    try:
        abc = int(str)
        if(abc > 1950 and abc < 2050):
            return abc
        else:
            return 0    #invalid number, screen for 0
    except:
        return -1

'''
Problem 3

What are the 50 most common words in the entire set of pages? 
(Ignore English stop words, which can be found, for example, here (Links to an external site.))
 Submit the list of common words ordered by frequency.
 
 STILL NEEDS TO ACCOUNT FOR STOP WORDS
 
 Thought Process: If I am understandign tokenization correctly, all words and their weights are stored in tokensCount.
 So in order to find the 50 most used words I just need to sort the key: vals of the dict into a list by decreasing
 weight value.
 
 After I have printed 50 entries, exit the method.
'''
def reportQuestion3():
    # read out token count dictionary from redis and convert to python dictionary
    dictionaryPython = r.hgetall(TOKEN_COUNT_NAME)
    diction = dict(json.loads(dictionaryPython[TOKEN_COUNT_KEY]))[TOKEN_COUNT_KEY]
    diction = dict(json.loads(diction))

    iLoop = 1
    file = open('tokensMostCount.txt', 'w+')
    # sort dict
    for w in sorted(diction, key=diction.get, reverse=True):
        # if a stopword ignore
        if (w in report.stopWords):
            continue

        if len(w) > 1:
            # print(w, diction[w])
            # screen for invalid numbers that aren't years
            result = _tryConvertToInt(str(w))
            if(result == 0):
                continue
            # write token and count
            file.write(str(iLoop) + ". " + str(w) + " " + str(diction[w]) + "\n")
        else:
            continue

        iLoop = iLoop + 1

        if iLoop > 50:
            break

    file.close()


'''
Problem 4

How many subdomains did you find in in the ics.uci.edu domain? 
Submit the list of subdomains ordered alphabetically and the number 
of unique pages detected in each subdomain. The content of this list should 
be lines containing URL, number, for example:

Thought Process: Since we have a set of all the urls we have crawled, I need to filter through them to find sites
that are subdomains of ics.uci.edu. 

I iterate through the urls, checking if they have ics.uci.edu in the subdomain.
If they have it, store the url because it is part of ics.uci.edu subdomains.
Store the subdomain itself in a dict to reference later for unique page counts.

Iterate through the filtered pages, and lookup the subdomain they of ics.uci.edu they belong to.
Increment count by 1.
'''
def reportQuestion4():
    # get domain count from redis and convert to dict
    redisDict = r.hgetall(setDomainCount)
    iLoop = 1

    file = open('subdomainCount.txt', 'w+')
    # loop and write subdomains to file
    for i in sorted(redisDict):
        file.write(str(iLoop) + ". " + str(i) + " " + str(redisDict[i]) + "\n")
        #print((i, redisDict[i]))
        iLoop = iLoop + 1


#if __name__ == "__main__":
    #reportQuestion3()
    #reportQuestion4()