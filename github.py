import json
from typing import Dict
import re
import os
import subprocess
import streamlit as st
from streamlit_autorefresh import st_autorefresh


st.set_page_config(layout='wide')
st_autorefresh(interval=15 * 60 * 1_000)

USER = os.environ.get("GH_EVENTS_USER", "entilzha")

COMMAND = f"""gh api \
        -H "Accept: application/vnd.github+json" \
        /users/{USER}/events?per_page=100
"""

st.cache(ttl=120)
def list_events():
    return json.loads(subprocess.run(COMMAND, shell=True, check=True, capture_output=True, text=True).stdout)


def rename_type(name: str):
    name = name.replace('Event', '')
    return ' '.join(re.findall('[A-Z][^A-Z]*', name))


def parse_event(event: Dict):
    repo = event['repo']['name']
    repo_url = f'https://github.com/{repo}'
    event_type = event['type']
    payload = event['payload']
    match event_type:
        case 'PushEvent':
            committer = payload['commits'][0]['author']['name']
            message = payload['commits'][0]['message']
            commit_url = payload['commits'][0]['url'].replace('api.', '')
            return f'[Commit](commit_url) by {committer} on [{repo}]({repo_url}): {message}'
        case 'IssueCommentEvent':
            commenter = payload['comment']['user']['login']
            comment_url = payload['comment']['html_url']
            return f'[Comment by {commenter} on {repo}]({comment_url})'
        case 'PullRequestEvent':
            pr = payload['pull_request']
            pr_url = pr['html_url']
            title = pr['title']
            requester = pr['user']['login']
            return f'[PR by {requester} on {repo}]({pr_url}): {title}'
        case _:
            return rename_type(event['type'])


FILTERED_EVENTS = set(['WatchEvent', 'ForkEvent', 'CreateEvent', 'PullRequestReviewEvent', 'PullRequestReviewCommentEvent'])


def event_filter(event):
    if event['type'] in FILTERED_EVENTS:
        return False
    elif event['type'] == 'PullRequestEvent':
        if event['payload']['action'] == 'closed':
            return False
        else:
            return True
    else:
        return True


st.header(f"Github: Activity List for {USER}")

all_events = [e for e in list_events() if event_filter(e)]

recent_repos = {event['repo']['name'] for event in all_events}

st.subheader("Recently Active Repositories")

for r in recent_repos:
    st.write(f"[{r}](https://github.com/{r})")


st.subheader("Recent Events")
rows = ["|Repo|Type|Content|", "|--|--|--|"]

for event in all_events:
    repo = event['repo']['name']
    repo_info = f'[{repo}](https://github.com/{repo})'
    event_info = event['type'].replace('Event', '')
    content = parse_event(event).replace('\n', ' ')[:200]
    rows.append(f'{repo_info}|{event_info}|{content}|')

st.markdown('\n'.join(rows))