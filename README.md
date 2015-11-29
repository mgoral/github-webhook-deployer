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

        # directory to which application should be deployed
        #
        "deploy_dir" : "/var/www/example.com/my-super-app/html",

        # http address of git repository
        #
        "git_http_address" : "https://github.com/username/some-application.git",

        # optional 'secret' field, as specified in webhook settings
        #
        "github_secret" : "supersecretkey111111eleven!!!",
    },
}
```

# Makefile

Some extra environment variables are available in your Makefiles:

```
$(DEPLOY_DIR) : equals to webhook_settings["username/app"]["deploy_dir"]
```
