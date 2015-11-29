Simple uWSGI application which handles deploying applications via Github webhook's `push` events.

To deploy the application the following steps are performed:

1. Repository clone (or pull if it was cloned before)
2. Application build via `make`
3. Application deployment via `make deploy`

As you can see, it is assumed that Makefile is present in application's root directory, and that it
contains `all` and `deploy` targets.

# settings.py

Configuration should be stored in the same directory as `wsgi.py`. It's a simple Python file called
`settings.py` and has the following format:

```
# specifies whether application should return some debug informations (aside
# of server response). These can be investigated on Github's webhook page in a
# "Response -> Body" textarea.
#
enable_debug = False

webhook_settings = {

    # each application has unique key which equals to its full name (username/repo)
    # several applications can be specified this way
    #
    "username/some-application" : {

        # only push events from this branch will be accepted
        #
        "prod_branch" : "master",

        # http address of git repository
        #
        "git_address" : "https://github.com/username/some-application.git",

        # optional 'secret' field, as specified in webhook settings
        #
        "github_secret" : "supersecretkey111111eleven!!!",
    },
}
```

If any field ends with a `_dir`, it will be expanded to the full path (so it can be e.g.
`~/some/dir/in/home`).

# Makefile

For each of your applications all settings, except `github_secret`, are exported as upper-case-named
environment variables with a `WEBHOOK_` prefix, so they can be easily accessed in from Makefile.

```
# settings.py:

enable_debug = True

webhook_settings = {
    "user/app" : {
        "prod_branch" : "master",           # available as $(WEBHOOK_PROD_BRANCH)
        "github_secret" : "asdfasd",        # not available
        "deploy_dir" : "~/app_deployment",  # $(WEBHOOK_DEPLOY_DIR) is e.g.  /home/www-data/app_deployment
        "build dir" : "build"               # $(WEBHOOK_BUILD_DIR)
    }
}

# Makefile:

all:
    mkdir $(WEBHOOK_BUILD_DIR)
    echo "Hello!" > $(WEBHOOK_BUILD_DIR)/index.html

deploy:
    cp -rf $(WEBHOOK_BUILD_DIR) $(WEBHOOK_DEPLOY_DIR)
```
