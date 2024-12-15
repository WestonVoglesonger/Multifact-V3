# Contributing

If you would like to contribute to the Edge-Carolina repository, forking the repository and making changes in your fork is the best approach. This keeps the main repository clean for official use by the project maintainers.

Forking creates a complete copy of the repository in your own GitHub account, where you can work on updates risk-free. Then you can submit a pull request back to the main repository for the project owners to review and potentially merge your changes.

## Forking the Repository

1. Navigate in a web browser to the Edge-Carolina repository on GitHub

2. Click on the 'Fork' button in the top right corner. Forking creates a complete copy of the repository in your own GitHub account. This allows you to freely edit the code without impacting the main repository.

3. After the fork process completes, you will now have a copy of the Edge-Carolina repository in your-GitHub-username/Edge-Carolina. This is your working repo.

## Cloning Your Fork Locally

Next you should clone your fork to your local machine:

1. On your forked repository, click on the 'Code' button to view the clone URL

2. Copy the HTTPS clone URL

3. Type git clone <clone-url> into your terminal to clone your forked repository locally

`git clone https://github.com/YOUR-USERNAME/Edge-Carolina.git`

This will create a local copy of the repository for you to work on.

## Syncing Your Fork

To keep your fork up to date as the main repository progresses:

1. Set the upstream remote repository link

`git remote add upstream https://github.com/WestonVoglesonger/Edge-Carolina.git`

2.Fetch updates from the upstream repository

`git fetch upstream`

3.Merge the main repository changes into your fork

```
git checkout main
git merge upstream/main
```
## Making & Submitting Changes

After syncing your fork, make any desired changes locally. Commit and push them to your fork:

```
git add .
git commit -m "Your commit message"
git push origin <Your branch>
```

When ready, submit a pull request to the main Edge-Carolina repository with your changes. Project owners can then review and potentially merge them.
