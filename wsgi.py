#-*- coding: utf-8 -*-

# Copyright (C) 2015 Michal Goral.
# 
# This file is part of github-webhook-deployer
# 
# github-webhook-deployer is free software: you can redistribute it 
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
# 
# github-webhook-deployer is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with github-webhook-deployer. If not, see 
# <http://www.gnu.org/licenses/>.

import os
import json
import hmac
import hashlib
import git
import subprocess

from settings import webhook_settings
from settings import enable_debug

script_dir = os.path.dirname(os.path.realpath(__file__))
main_checkout_dir = os.path.join(script_dir, ".site-sources")

def call(cmd):
    return subprocess.check_call(cmd, shell=True)

def validate_request(signature, payload, req_settings):
    if signature is None:
        return False

    sha_name, signature = signature.split('=')
    if sha_name != "sha1":
        return False

    # HMAC requires its key to be bytes, but data is
    # strings.
    m = hmac.new(req_settings["github_secret"].encode("utf-8"), msg=payload, digestmod=hashlib.sha1)
    return hmac.compare_digest(m.hexdigest(), signature)

def return_body(msg):
    if enable_debug is True:
        return [msg.encode("utf-8")]
    return []

def read_request(environ):
    signature = environ.get('HTTP_X_HUB_SIGNATURE')

   # the environment variable CONTENT_LENGTH may be empty or missing
    try:
        payload_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        payload_size = 0

    payload = environ['wsgi.input'].read(payload_size)

    if environ.get("REQUEST_METHOD") != "POST":
        raise ValueError("Incorrect request method")

    if environ.get("CONTENT_TYPE").lower() != "application/json":
        raise ValueError("Incorrect content type")

    if environ.get("HTTP_X_GITHUB_EVENT").lower() != "push":
        raise ValueError("Unsupported git event")

    return payload

def get_checkout_dir(req_settings):
    return os.path.join(main_checkout_dir, req_settings["full_name"])

def checkout(request, req_settings):
    if req_settings["git_address"].startswith("http"):
        compare_addr = request.get("repository", dict()).get("clone_url")
    else:
        compare_addr = request.get("repository", dict()).get("ssh_url")

    if compare_addr != req_settings["git_address"]:
        raise ValueError("requested repository mismatch")

    if request.get("ref") != "refs/heads/%s" % req_settings["prod_branch"]:
        return False

    checkout_dir = get_checkout_dir(req_settings)

    try:
        repo = git.Repo(checkout_dir)
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as e:
        repo = git.Repo.clone_from(req_settings["git_address"], checkout_dir)

    g = git.cmd.Git(checkout_dir)
    g.clean(f=True, d=True)
    g.reset(hard=True)
    g.checkout(req_settings["prod_branch"])
    g.pull()

    head_sha1 = g.log(n=1, pretty="%H")
    if head_sha1 != request.get("head_commit", dict()).get("id"):
        raise ValueError("HEAD and requested commit mismatch")

    return True

def set_env(req_settings):
    for key, val in req_settings.items():
        if key.lower() == "github_secret":
            continue

        good_key = key.replace(" ", "_").upper()
        good_val = str(val)

        if good_val.lower().endswith("_dir"):
            good_val = os.path.abspath(os.path.expanduser(good_val))

        os.environ["WEBHOOK_%s" % good_key] = good_val

def build(req_settings):
    checkout_dir = get_checkout_dir(req_settings)
    call("cd '%s' && make" % checkout_dir)

def deploy(req_settings):
    checkout_dir = get_checkout_dir(req_settings)
    call("cd %s && make deploy" % checkout_dir)

def application(environ, start_response):
    try:
        payload = read_request(environ)
    except ValueError as e:
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return return_body(str(e))

    try:
        request = json.loads(payload.decode("utf-8"))
    except Exception as e:
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return return_body("Incorrect request: not a JSON format.")

    full_name = request.get("repository", dict()).get("full_name")
    if full_name is None:
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return return_body("missing full_name")

    req_settings = webhook_settings.get(full_name)
    if req_settings is None:
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return return_body("server-side webhook not configured for '%s'" % full_name)
    else:
        req_settings["full_name"] = full_name

    if "github_secret" in req_settings and validate_request(environ.get("HTTP_X_HUB_SIGNATURE"), payload, req_settings) is False:
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return return_body("Incorrect signature")

    try:
        set_env(req_settings)
        checkout(request, req_settings)
        build(req_settings)
        deploy(req_settings)
    except Exception as e:
        start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
        return return_body(str(e).encode("utf-8"))

    start_response('200 OK', [('Content-Type', 'text/html')])
    return []
