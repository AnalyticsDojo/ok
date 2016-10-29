import datetime
from flask import url_for
import pygal
import server.highlight as highlight

### Common Functions ###
def get_unique_backups(backups):
    """
    Given a list of backups, only include backups that have changed.
    Returns a list of (backup, lines_changed) tuples AND
    a map from all backup_ids to their "kept" backup_id AND
    a map from kept backup_ids to their index
    Can assume that for every returned backup:
        - a .files() section exists
        - diff between backup_i and backup_i+1 exists
    TODO: should CACHE this?
    """
    filtered = []
    id_map = {} # maps all backup hashid to a kept backup's hashid
    index_map = {} # maps from all kept backups to its index
    index = 1
    for i in range(len(backups)):
        # edge case for first backup
        if not i and backups[i] and backups[i].files():
            filtered.append((backups[i], -1))
            last_unique_id = backups[i].hashid
            id_map[backups[i].hashid] = last_unique_id
            index_map[backups[i].hashid] = 0
            continue

        prev_backup, curr_backup = backups[i - 1], backups[i]
        prev_code, curr_code = prev_backup.files(), curr_backup.files()

        # ensure code exists
        if not (prev_code and curr_code):
            id_map[curr_backup.hashid] = last_unique_id
            continue

        # only keep with diffs
        lines_changed = highlight.diff_lines(prev_code, curr_code)
        if lines_changed:
            filtered.append((curr_backup, lines_changed))
            last_unique_id = curr_backup.hashid
            index_map[curr_backup.hashid] = index
            index += 1
        id_map[curr_backup.hashid] = last_unique_id

    assert (len(index_map) == index) #todo remove
    return filtered, id_map, index_map

def get_time_diff_seconds(analytics1, analytics2):
    """
    Assumes both analytics1 and analytics2 exists.
    returns None iff a `time` field is not included in either analytics1 or analytics2
    returns integer (time diff in seconds) otherwise
    """
    time1_string, time2_string = analytics1.get("time"), analytics2.get("time")
    if not (time1_string and time2_string):
        return None
    time_format = "%Y-%m-%d %X"
    time1 = datetime.datetime.strptime(time1_string.split(".")[0], time_format)
    time2 = datetime.datetime.strptime(time2_string.split(".")[0], time_format)
    time_difference = time2 - time1
    return time_difference.total_seconds()

### Diff Overview Generation ###
def get_backup_range(backups, commit_id, bound=10):
    """
    Naive Implementation
    Returns a dictionary: {
        "backups": backups,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id
        "next_commit_id": next_commit_id
    }
    backups = unique backups `bound` away from backup with `commit_id`
    prev/next_commit_id = prev/next commit_id not part of backups
    """
    unique_backups_tuples, id_map, index_map = get_unique_backups(backups)
    unique_backups = [backup_tuple[0] for backup_tuple in unique_backups_tuples]
    # invalid commit_id
    if commit_id not in id_map:
        return {}

    # find included commit_id
    commit_id = id_map[commit_id]

    commit_index = index_map[commit_id]

    # get prev and curr ids
    prev_commit_id = unique_backups[max(0, commit_index-bound-1)].hashid
    next_commit_id = unique_backups[min(len(unique_backups)-1, commit_index+bound+1)].hashid

    unique_backups = unique_backups[max(0, commit_index-bound-1)\
                                    :min(len(unique_backups), commit_index+bound+1)]
    return {
        "backups": unique_backups,
        "prev_commit_id": prev_commit_id,
        "commit_id": commit_id,
        "next_commit_id": next_commit_id
    }

def get_diffs_and_stats(backups):
    """
    Given a list of backups, returns 2 lists.
    A list of diffs, and list of stats corresponding to each diff.
    Assumptions made on backups: 
        - all backups have code (.files() is not None)
        - all backups have unique code
        - suggested usage: call `get_unique_backups` or `get_backup_range`
    """
    files_list, stats_list = [], []
    for i, backup in enumerate(backups):
        if not i: # first unique backup => no diff
            continue

        prev = backups[i - 1].files()
        curr = backup.files()
        files = highlight.diff_files(prev, curr, "short")
        files_list.append(files)

        backup_stats = {
            'submitter': backup.submitter.email,
            'commit_id' : backup.hashid,
            'question': None,
            'time': None,
            'passed': None,
            'failed': None
        }

        analytics = backup and backup.analytics()
        grading = backup and backup.grading()

        if analytics:
            backup_stats['time'] = analytics.get('time')

        if grading:
            questions = list(grading.keys())
            question = None
            passed, failed = 0, 0
            for question in questions:
                passed += grading.get(question).get('passed')
                passed += grading.get(question).get('failed')
            if len(questions) > 1:
                question = questions

            backup_stats['question'] = question
            backup_stats['passed'] = passed
            backup_stats['failed'] = failed
        else:
            unlock = backup.unlocking()
            backup_stats['question'] = "[Unlocking] " + unlock.split(">")[0]

        stats_list.append(backup_stats)
    return files_list, stats_list

### Graph Generation ###
def get_graph_stats(backups):
    """
    Given a list of backups, return a list of statistics for the unique ones
    The len(list) should be 1 less than the number of unique usuable backups
    """
    unique_backups_tuples = get_unique_backups(backups)[0] # should be cached

    stats_list = []
    for i in range(len(unique_backups_tuples)):
        if not i: # first unique backup => no diff
            continue

        prev_backup, curr_backup = unique_backups_tuples[i - 1][0], unique_backups_tuples[i][0]
        curr_lines_changed = unique_backups_tuples[i][1] # stored in tuple!
        prev_analytics = prev_backup and prev_backup.analytics()
        curr_analytics = curr_backup and curr_backup.analytics()

         # ensure analytics exists
        if not (prev_analytics and curr_analytics):
            continue

        # get time differences
        diff_in_secs = get_time_diff_seconds(prev_analytics, curr_analytics)
        if diff_in_secs == None or diff_in_secs < 0:
            continue

        diff_in_mins = diff_in_secs // 60 + 1 # round up

        # get ratio between curr_lines_changed and diff_in_mins
        lines_time_ratio = curr_lines_changed / diff_in_mins

        stats = {
            'submitter': curr_backup.submitter.email,
            'commit_id' : curr_backup.hashid,
            'lines_changed': curr_lines_changed,
            'diff_in_secs': diff_in_secs,
            'diff_in_mins': diff_in_mins,
            'lines_time_ratio': lines_time_ratio
        }
        stats_list.append(stats)
    return stats_list

def get_graph_points(backups, cid, email, aid, extra):
    """
    Given a list of backups, forms the points needed for a pygal graph
    """
    stats_list = get_graph_stats(backups)
    def gen_point(stat):
        value = stat["lines_time_ratio"]
        lines_changed = round(stat["lines_changed"], 5)
        label = "Total Lines:{0} \n Submitter: {1} \n Commit ID: {2}\n".format(
            lines_changed, stat["submitter"], stat["commit_id"])
        url = url_for('.student_commit_overview', 
                cid=cid, email=email, aid=aid, commit_id=stat["commit_id"])

        #arbitrary boundaries for color-coding based on ratio, need more data to determine bounds
        if lines_changed > 100: 
            color = 'red'
        elif lines_changed > 50:
            color = 'orange'
        elif lines_changed > 15:
            color = 'blue'
        else:
            color = 'black'

        if extra:
            url += "?student_email=" + email
        return {
            "value": value,
            "label" : label,
            "xlink": url,
            "color": color
        }
    points = [gen_point(stat) for stat in stats_list]
    return points

def generate_line_chart(backups, cid, email, aid, extra):
    """
    Generates a pygal line_chart given a list of backups
    """
    points = get_graph_points(backups, cid, email, aid, extra)

    line_chart = pygal.Line(disable_xml_declaration=True,
                            human_readable=True,
                            legend_at_bottom=True,
                            pretty_print=True
                            )
    line_chart.title = 'Lines/Minutes Ratio Across Backups'
    line_chart.add('Backups', points)
    return line_chart
