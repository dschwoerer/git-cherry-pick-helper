#!/usr/bin/env python3
# coding: utf-8
from git import Repo
from subprocess import Popen, STDOUT, PIPE, call as subprocesscall
from difflib import SequenceMatcher
import numpy as np
import sys
import readline

import atexit
import os


__version__ = "0.1.0"


def cmd(cmd, allow_failure=False):
    status = subprocesscall(cmd, shell=True)
    if allow_failure:
        return status
    assert status == 0, f"{cmd} failed with exit code {status}"


def run(cmd, allow_failure=False):
    if runopts["dry"]:
        print("would execute:", cmd)
        if allow_failure:
            return 0, ""
        return ""
    child = Popen(cmd, stderr=STDOUT, stdout=PIPE, shell=True)
    # This returns a b'string' which is casted to string in
    # python 2. However, as we want to use f.write() in our
    # runtest, we cast this to utf-8 here
    output = child.stdout.read().decode("utf-8", "ignore")
    # Wait for the process to finish. Note that child.wait()
    # would have deadlocked the system as stdout is PIPEd, we
    # therefore use communicate, which in the end also waits for
    # the process to finish
    child.communicate()
    if allow_failure:
        return child.returncode, output
    assert child.returncode == 0
    return output


def clean_git_show(commit):
    diff = run(f"git show {commit}")
    out = []
    for line in diff.split("\n"):
        if line.startswith("commit "):
            continue
        if line.startswith("index "):
            continue
        if line.startswith("@@"):
            continue
        out.append(line)
    return "\n".join(out)


def meld(*args):
    largs = len(args)
    worst = similar(*args)
    if largs > 2:
        sims = np.ones((largs, largs))
        for i in range(largs):
            for j in range(i):
                sims[i, j] = similar(args[i], args[j])
        ij = np.argmin(sims)
        i, j = ij // largs, ij % largs
        args = args[i], args[j]
        assert worst >= similar(*args)
    for f, t in zip("ab", args):
        with open(".gcph." + f, "w") as f:
            f.write(t)
    cmd("meld .gcph.a .gcph.b")


def set_state():
    pass


def set_dryrun(opts):
    opt = _single_from_input(opts, True, "Can only enable or disable dryrun.")
    runopts["dry"] = {"false": False, "true": True}[opt]


def set_merge(opts):
    opt = _single_from_input(opts, True, "Can only enable or disable an option.")
    runopts["merge"] = {"false": False, "true": True}[opt]


def set_show_black(opts):
    opt = _single_from_input(opts, True, "Can only enable or disable an option.")
    runopts["show_blacklisted"] = {"false": False, "true": True}[opt]


def print_options(opts):
    CONT


def set_ignore_branches(opts):
    set_many_branches(opts, "ignore")


def set_many_branches(opts, name):
    global runopts
    for opt in set(opts):
        if opt:
            runopts["ignore"].append(opt)


def set_source(opts):
    set_single_branch(opts, "source")


def set_onto(opts):
    set_single_branch(opts, "onto")


def _single_from_input(opts, default, error):
    opts = set([x for x in opts if x])
    if len(opts) == 0:
        opts = ["HEAD"]
    if len(opts) != 1:
        raise ValueError(error)
    for opt in opts:
        return opt


def set_single_branch(opts, name):
    global runopts
    runopts[name] = _single_from_input(
        opts, "HEAD", f"Can only set a single branch for {name}"
    )


def get_branch(branch):
    if branch == "HEAD":
        return repo.head
    #    print(branch, type(branch))
    return repo.refs[branch]


def wait_user(msg):
    input(msg + " (type enter to continue)")


def runit(args):
    if not runopts["onto"]:
        raise ValueError("Need to `set onto` to specify onto which branch to rebase to")
    for branch, commits in current_branches.items():
        cmd(f"git checkout {runopts['onto']}")
        cmd(f"git checkout -b {branch}")
        for com in commits[::-1]:
            s = cmd(f"git cherry-pick {com}", allow_failure=True)
            if s:
                while repo.is_dirty():
                    wait_user("Resolve the conflicts and commit the changes")
    print("Thank you for using gcph 🎉. Please call again 👋")
    sys.exit(0)


def fu():
    pass


repo_ref_str = None
runopts = dict(
    ignore=[],
    source="HEAD",
    onto=None,
    dry=False,
    merge=False,
    show_black=False,
)


def get_branches(text):
    global repo_ref_str
    if repo_ref_str is None:
        repo_ref_str = [str(x) for x in repo.refs]
    # print(repo_ref_str)
    return repo_ref_str


def myexit(*a):
    sys.exit(0)


def _complete(text, state, opts, cache=[]):
    if state == 0:
        for k in opts:
            # print(k, k.startswith(text))
            if k.startswith(text):
                cache.append(f"{k} ")
    if cache:
        return cache.pop(0)
    return None


def set_error(text):
    global raiseError
    text = _single_from_input(
        text, "print", "Error handling only allows a single value"
    )
    raiseError = {"raise": True, "print": False}[text]
    return


def get_line_buffer():
    return readline.get_line_buffer().split(";")[-1].lstrip()


def complete(text, state):
    try:
        parts = get_line_buffer().split(" ")
        subs = commands
        for part in parts[:-1]:
            subs = subs[part][1]
            if not isinstance(subs, dict):
                break

        if subs is None:
            opts = []
        elif isinstance(subs, dict):
            opts = subs.keys()
        elif isinstance(subs, list):
            opts = subs
        else:
            opts = subs(text)
        return _complete(text, state, opts)
    except Exception as e:
        print(e)
        raise


def less(data):
    process = Popen(["less"], stdin=PIPE)

    try:
        process.stdin.write(data)
        process.communicate()
    except IOError as e:
        pass


def _show_commit(commit):
    cmd(f"git show {commit}")


def myexec(x):
    x = x.strip()
    if not x:
        return
    parts = x.split(" ")
    subs = commands
    past = []
    while len(parts):
        part = parts.pop(0)
        past.append(part)
        try:
            temp = subs[part]
        except KeyError:
            msg = f"`{part}` is not a valid command"
            if len(past) > 1:
                msg = f"`{part}` is not a valid subcommand for `{' '.join(past[:-1])}`"
            if not part:
                msg = f"`{' '.join(past[:-1])}` requires an argument. Maybe try the tab completion?"
            raise ValueError(msg)
            return
        if temp[0] is not None:
            return temp[0](parts)
        subs = temp[1]


def comp_disp(a, b, c):
    print(a, b, c)


def deb1():
    print("x>", end=" ")


def similar(*args):
    args = [clean_git_show(x) for x in args]
    return _similar(*args)


def _similar(a, b, *args):
    allargs = a, b, *args
    if max([len(x) for x in allargs]) > 10000 and isinstance(a, str):
        return _fastsimilar(*allargs)
    ratio = SequenceMatcher(a=a, b=b).ratio()
    # ratio = nltk.edit_distance(a, b)
    if args:
        ratio = min(ratio, _similar(a, *args))
    return ratio


def _fastsimilar(*allargs):
    return _similar(*[x.split("\n") for x in allargs])


def get_all_parents(com):
    todo = [com]
    allp = set()
    while todo:
        x = todo.pop()
        if x not in allp:
            allp.add(x)
            yield x
            todo += x.parents


def update_commits(opts):
    _get_available_commits(
        get_branch(runopts["source"]),
        [get_branch(x) for x in (runopts["onto"], *runopts["ignore"])],
    )
    if not "quiet" in opts:
        print_commits(opts)


def print_info(opts):
    if "all" in opts:
        opts = range(len(commits))
    else:
        opts = [int(x) for x in opts if x]
    for opt in opts:
        com = commits[opt][0]
        _print_commit(opt)
        try:
            candidates = todel_by_date[com.authored_date]
        except KeyError:
            print("There are no known similar commits.")
            continue
        for cand in candidates:
            sim = similar(com, cand)
            _print_commit_other(cand, f"{sim*100:.1f}%")
        print()


def print_show(opts):
    if "all" in opts:
        opts = range(len(commits))
    else:
        opts = [int(x) for x in opts if x]
    for opt in opts:
        com = commits[opt][0]
        _show_commit(com)


def _print_commit(i):
    com, s = commits[i]
    fmt = f"%{_int_log10(len(commits))+1}d: %1s %7s %s"
    show = {"notin": "  ", "maybe": "❓", "picked": "✅", "ignored": "👻"}
    if s == "ignored" and not runopts["show_black"]:
        return
    print(fmt % (i, show[s], com.hexsha[:7], com.message.split("\n")[0]))


def _print_commit_other(com, pre=""):
    fmt = f"%{_int_log10(len(commits))+5}s %7s %s"
    print(fmt % (pre, com.hexsha[:7], com.message.split("\n")[0]))


def print_commits(opts):
    if commits is None:
        return update_commits()
    print("❓ maybe already picked    ✅ selected for picking")
    for i in range(len(commits)):
        _print_commit(i)
    if not runopts["show_black"]:
        hidden = len([s for c, s in commits if s == "ignored"])
        if hidden:
            print(f"Not showing {hidden} blacklisted commits")


current_branches = {}


def new_branch(opts):
    for opt in opts:
        if opt:
            current_branches[opt] = []


def delete_branch(opts):
    for opt in opts:
        if opt:
            current_branches.pop(opt)


def blacklist_commits(opts):
    global blacklist
    for opt in opts:
        if opt:
            opt = int(opt)
            commit = commits[opt][0]
            blacklist.append(str(commit))
            commits[opt] = commit, "ignored"


def write_blacklist_file(blacklist_file):
    with open(blacklist_file + ".tmp", "w") as f:
        for black in blacklist:
            f.write(black + "\n")
    os.rename(blacklist_file + ".tmp", blacklist_file)


def add_to_branch(opts):
    branch = opts.pop(0)
    if branch not in current_branches:
        current_branches = []
    for opt in opts:
        if opt:
            opt = int(opt)
            current_branches[branch].append(commits[opt][0])
            commits[opt] = commits[opt][0], "picked"


def suggest_add(text):
    cur = get_line_buffer().split(" ")
    if len(cur) > 2:
        return [str(x) for x in range(len(commits))]
    return current_branches.keys()


raiseError = False
blacklist = []


def current_commits_or_all(text):
    return ["all"] + [str(x) for x in range(len(commits))]


commands = {
    "source": (set_source, get_branches),
    "onto": (set_onto, get_branches),
    "ignore_branch": (set_ignore_branches, get_branches),
    "update": (update_commits, ["quiet"]),
    "print": (print_commits, None),
    "blacklist_commits": (blacklist_commits, current_commits_or_all),
    "add": (add_to_branch, suggest_add),
    "delete": (delete_branch, current_branches),
    "info": (print_info, current_commits_or_all),
    "show": (print_show, current_commits_or_all),
    "set": (
        None,
        {
            "error": (set_error, ["print", "raise"]),
            "dryrun": (set_dryrun, ["false", "true"]),
            "merge": (set_merge, ["false", "true"]),
            "show_blacklist": (set_show_black, ["false", "true"]),
            # "bla": (fu, None),
        },
    ),
    "run": (runit, None),
    "exit": (myexit, None),
}


def main():
    global repo
    repo = Repo(".")

    readline.set_completer(complete)
    readline.set_completer_delims(" \t\n;")
    # readline.set_pre_input_hook(deb1)
    readline.parse_and_bind("tab: complete")
    histfile = os.path.join(os.path.expanduser("~"), ".gcph_history")
    try:
        readline.read_history_file(histfile)
        # default history len is -1 (infinite), which may grow unruly
        readline.set_history_length(1000)
    except FileNotFoundError:
        pass
    atexit.register(readline.write_history_file, histfile)

    blacklist_file = os.path.join(os.path.expanduser("~"), ".gcph_blacklist")
    try:
        with open(blacklist_file) as f:
            global blacklist
            blacklist = [l.strip() for l in f]
    except FileNotFoundError:
        pass
    atexit.register(write_blacklist_file, blacklist_file)

    while True:
        try:
            x = input("gcph> ")
        except EOFError:
            print("exit")
            sys.exit(0)
        except KeyboardInterrupt:
            print("^C")
            sys.exit(3)
        try:
            for y in x.split(";"):
                myexec(y)
        except ValueError as e:
            global raiseError
            if raiseError:
                raise
            print(f"ERROR: {e}")


def _int_log10(x):
    ret = 0
    while x:
        x //= 10
        ret += 1
    return ret


commits = None
todel_by_date = None


def _get_available_commits(include, excludes):
    ap = list(get_all_parents(include.commit))
    # aps = [str(x) for x in ap]

    this = set(ap)
    todel = set()
    for ex in excludes:
        todel.update(get_all_parents(ex.commit))
    global todel_by_date
    todel_by_date = {}
    for d in todel:
        this.discard(d)
        date = d.authored_date
        if date not in todel_by_date:
            todel_by_date[date] = []
        todel_by_date[date].append(d)

    global commits
    commits = sorted(this, key=lambda a: a.authored_date, reverse=True)
    # print(len(commits), "that are not identical")
    cleaned_commits = []
    blackset = set(blacklist)
    picked = set()
    for comms in current_branches.values():
        picked.update(comms)
    for c in commits:
        if not runopts["merge"]:
            if len(c.parents) > 1:
                continue
        if c in picked:
            cleaned_commits.append((c, "picked"))
            continue
        if str(c) in blackset:
            cleaned_commits.append((c, "ignored"))
            continue
        try:
            candidates = todel_by_date[c.authored_date]
        except KeyError:
            cleaned_commits.append((c, "notin"))
            continue
        sim = similar(c, *candidates)
        if sim < 1:
            cleaned_commits.append((c, "maybe"))
    commits = cleaned_commits


if __name__ == "__main__":
    main()
