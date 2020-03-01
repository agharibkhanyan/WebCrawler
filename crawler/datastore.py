from collections import defaultdict

class DataStore:
    #team_utils could not pickup self.robotsCheck property without below declaration
    robotsCheck = dict()
    subDomainCount = dict()
    tokensCount = dict()   #all tokens stored in dict with counts
    urlSeenBefore = set() #unique urls for report, len(urlSeenBefore) = #
    blackList = set()
    mostTokensUrl = ["", 0] #[url, count]
    uniqueUrlCount = 0
    icsUrlCount = 0
    icsSubDomains = defaultdict(int)

    def __init__(self):
        self.robotsCheck = dict()
        self.subDomainCount = dict()
        self.tokensCount = dict()
        self.urlSeenBefore = set()
        self.blackList = set()
        self.frontier = set()
        # Read robots.txt for all domains and store in dict
        #tutils.robotsTxtParse()

        print()