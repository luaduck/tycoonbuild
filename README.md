# TycoonBuild IS DEPRECATED

Please use [cdn\_version\_scraper](https://github.com/ropenttd/cdn_version_scraper) for future projects, and consider migrating if you are using it. This tool will no longer be updated.


_A /r/openttd tool_

### Where are the builds?

This tool generates builds that are pushed to [redditopenttd/openttd](https://hub.docker.com/r/redditopenttd/openttd/).

## About TycoonBuild

TycoonBuild is an automated tool designed to make maintenance of OpenTTD Docker builds far less painful.

Right now, it:
 * scrapes the _openttd.org_ release information server (https://openttd.ams3.digitaloceanspaces.com/openttd-releases/listing.txt) every 60 seconds
 * detects any changes / new versions and saves their state to `builds.json`
 * dispatches required builds to a (local) Docker server
 * correctly tags and pushes them once build is complete
 * updates `builds.json` with state after build is complete to indicate that the build was successful, and not to repeat builds for that version

TycoonBuild is currently very focused on building packages for `redditopenttd/openttd`, but it should be easy to fork to suit your individual needs. Pull requests making it more agnostic are much appreciated.
