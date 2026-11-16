# Space Apps 2026, Dushanbe, in numbers

A static page with charts about the NASA Space Apps Challenge 2026 local event in Dushanbe: 173 teams, 125 submitted projects, how they were built, what a browser test found on the project sites, and when the code was written.

Live page: https://billsharifzade.github.io/space_apps_stats/

- **Source.** The public team and project pages of the [Dushanbe local event](https://www.spaceappschallenge.org/2026/local-events/dushanbe/?tab=teams), read on 16 November 2026, plus the public project sites and GitHub repositories that the submissions link to.
- **Privacy.** Member names are not published here, only the number of members per team.
- **It counts and measures; it does not judge the projects.** The browser test opened each site once, clicked up to ten controls and typed nothing.
- **Not affiliated** with NASA or the Space Apps organisers.

`tools/` holds the scripts that fetched the data, checked the links, tested the sites (`probe.mjs`), read the repositories (`repos.py`) and built `data.js`. The page itself is `index.html` with no build step.
