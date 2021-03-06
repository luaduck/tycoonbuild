import copy
import time, datetime, requests, os, json, yaml
import docker


def logThis(msg, end='\n'):
    print(datetime.datetime.utcnow().strftime("%x %H:%M:%S | " + msg), end=end)


class Scraper(object):
    def Scrape(self):
        page = requests.get('https://cdn.openttd.org/openttd-releases/latest.yaml')
        if page.status_code == 200:
            self.page = page.text
            self.data = []  # clean house
            latestVersions = yaml.load(self.page, Loader=yaml.FullLoader).get('latest')
            for data in latestVersions:
                thisver = {'version': data.get('version'), 'date': data.get('date'), 'tag': data.get('name')}
                self.data.append(thisver)
            logThis("Scrape succeeded")
        else:
            logThis("Scrape failed!")

    def Process(self):
        newJobsFlag = False
        for target, data in self.targets.items():
            allPossibleBuildTargets = list(x for x in self.data
                                if x.get('tag', None) == data.get('tag')
                                and data.get('search', '').upper() in x.get('version').upper()
                                )

            if len(allPossibleBuildTargets) == 0:
                succ = False
                for alternate in data['upgrade']:
                    copyBuild = self.knownBuilds.get(alternate, False)
                    allPossibleBuildTargets = [copy.copy(copyBuild)]
                    if allPossibleBuildTargets[0]:
                        logThis("Target " + target + ': unavailable, superceded by ' + buildTarget['version'])
                        allPossibleBuildTargets[0]['tags'] = data['tags']
                        succ = True
                        break
                if not succ:
                    logThis("Target " + target + ': unavailable and no supercession available, skipping')
                    break

            buildTarget = max(allPossibleBuildTargets, key=(lambda key: key['date']))

            buildTarget['tags'] = data['tags']  # we tag early so that we can easily compare

            if self.knownBuilds.get(target, {}) == buildTarget:
                # we already have the build, have we processed it?
                if self.finishedBuilds.get(target, {}) == buildTarget:
                    logThis("Target " + target + ': version ' + buildTarget[
                        'version'] + " already built, skipping")
                    continue
                else:
                    logThis("Build target for " + target + ': version ' + buildTarget[
                        'version'] + " detected as failed, requeuing")
            else:
                logThis("New build target for " + target + ': version ' + buildTarget['version'])
            self.knownBuilds[target] = buildTarget
            self.jobs.append(buildTarget)
            newJobsFlag = True
        self.SaveState()
        if not newJobsFlag:
            logThis("No new targets")
        return newJobsFlag

    def DispatchJobs(self):
        garbage = []
        for job in self.jobs:
            logThis("Building " + job['version'] + " for " + ','.join(job['tags']))
            image = self.docker.images.build(
                path=os.environ.get('DOCKER_BUILDDIR', '/Users/duck/Documents/Workbench/Docker/OpenTTD'),
                rm=True,
                buildargs={'OPENTTD_VERSION': job['version']},
                tag=self.repo + ':' + job['version'])
            for tag in job['tags']:
                image.tag(self.repo, tag)
            logThis("done!")
            garbage.append(job)

        logThis("Builds complete, uploading (this might take a moment)")
        self.docker.images.push(self.repo)
        for job in garbage:
            self.finishedBuilds[job['tag']] = job
            self.jobs.remove(job)

        logThis("Upload complete")
        self.SaveState()

    def LoadState(self):
        def date_hook(json_dict):
            for (key, value) in json_dict.items():
                try:
                    json_dict[key] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")
                except:
                    pass
            return json_dict
        try:
            with open('builds.json') as fp:
                try:
                    filedata = json.load(fp, object_hook=date_hook)
                    self.knownBuilds = filedata.get('known', {})
                    self.finishedBuilds = filedata.get('built', {})
                    logThis("Loaded builds from builds.json")
                except json.decoder.JSONDecodeError:
                    json.dump({}, open('builds.json', 'w'))
        except FileNotFoundError:
            pass

    def SaveState(self):
        with open('builds.json', 'w') as fp:
            json.dump({'known': self.knownBuilds, 'built': self.finishedBuilds}, fp, default=str)

    @classmethod
    def Run(cls, scraper):
        cls.Scrape(scraper)
        newjobs = cls.Process(scraper)
        if newjobs:
            # Dey took our jerbs!
            logThis("Processing new jobs")
            cls.DispatchJobs(scraper)

    def __init__(self):
        self.data = []
        self.targets = {'stable': {'tag': 'stable', 'tags': ['stable', 'latest']},
                        'testing_rc': {'tag': 'testing', 'tags': ['rc'], 'search': 'RC', 'upgrade': ['stable']},
                        'testing_beta': {'tag': 'testing', 'tags': ['beta'], 'search': 'beta',
                                         'upgrade': ['testing_rc', 'stable']}}
        self.jobs = []
        self.knownBuilds = {}
        self.finishedBuilds = {}
        self.LoadState()
        self.repo = 'redditopenttd/openttd'
        self.docker = docker.from_env()
        if os.environ.get('DOCKER_USER', False):
            try:
                self.docker.login(os.environ.get('DOCKER_USER', None), os.environ.get('DOCKER_PASS', None))
            except docker.errors.DockerException as e:
                print(e)


if __name__ == '__main__':
    scraper = Scraper()
    while True:
        Scraper.Run(scraper)
        time.sleep(60)
