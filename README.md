# git-cherry-pick-helper

The tool aims to help with chaotic git workflows.

It provides a small shell with tab completion.

## The Problem

Working on feature branches is good practice and should be done. However, I
often end up using a production branch that has diverged from upstream.  I do
merge some of my feature branches.  I also commit directly to this branch.
Then I need to cherry-pick back onto the feature branches.

When I then later merge the upstream branch, git does not remove my
cherry-picked commit. `git log` does not help with identifying which commits
might still be applicable for upstream.

git-cherry-pick-helper shows what commits are only in the current branch and not upstream.

It allows to also exclude additional branches, which you might have pull
requests open. You can also blacklist commits that are not suitable for
upstream.  It excludes commits that are cherry-picked. If the commit is not
cleanly applied and modified, it still shows the commit, and can tell you how
similar they are.

## Example workflow

```
$ cd path/to/repo # or worktree
$ git stash # make sure this is in a clean state to avoid issues; optional
$ git-cherry-pick-helper
# Set which branch we want to take commits from
gcph> source mydevbranch
# We want to add those commits to a clean upstream branch
gcph> onto origin/next
# Ignore all commits that are already in feature branches
gcph> ignore origin/my-pr1 feature2
# Look what commits we might want to add print that
gcph> update
# If there is something we need to add to a new branch we can do this with
gcph> new my-new-feature
# Select feature branches by the above printed id
gcph> add my-new-feature 1 4 7
# Print the overview again and see what commits we have selected for inclusion
gcph> print
# If we are happy we can apply the change set
gcph> run
```

Different commands can be put in the same line, separted by `;` - this makes the history even more useful:

```
gcph> source mydevbranch ; onto origin/next ; ignore origin/my-pr1 feature2 ; update
```

## All commands

 * `source <branch>` set the source branch from which to cherry-pick commits.
 * `onto <branch>` set the branch onto which to add commits.
 * `ignore_branch <branch> [<branch> ...]` set the branch(es) of which all commits are excluded,
   e.g. commits that are already cherry-picked.
 * `update [quiet]` Update what commits are available.
 * `print` Print the current state.
 * `blacklist_commits <commit> [<commit> ...]` Set commits to be ignored. Note
   that the commits will be permanently blacklisted. This can be undone by
   modifying `~/.gcph_blacklist`.
 * `add <new-branch> <commit-id> [<commit-id> ...]` Add commits to a new
   branch.
 * `delete <new-branch>` Delete a previous created branch.
 * `info <commit-id> [<commit-id> ...]` Show what commits are similar and how
   similar they are.
 * `show <commit-id> [<commit-id> ...]` Show the commit, similar to `git show`.
 * `run` Execute the changes and create new branches.
 * `exit` Exit without commiting any changes.
 
