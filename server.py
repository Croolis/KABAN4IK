import gevent.monkey
gevent.monkey.patch_all()

import bottle
bottle.debug(True)

import gevent.wsgi

from bottle import route, run, request, response, static_file, abort

import spur

import config

def send_key(username, host):
    #send key
    local_shell = spur.LocalShell()
    local_shell.run(["scp", "-i", config.ADMIN_KEY_PATH, config.KEY_STORAGE_PATH % username,
     "ubuntu@%s:%s/%s.pub" % (host, config.ADMIN_HOME, username)])

    shell = spur.SshShell(hostname=host, username=config.ADMIN_USERNAME,
        private_key_file=config.ADMIN_KEY_PATH,
        missing_host_key=spur.ssh.MissingHostKey.warn)

    # create user
    shell.run(["sudo", "useradd", "-m", username])
    shell.run(["sudo", "usermod", "-aG", "sudo", username])
    shell.run(["sudo", "mkdir", "/home/%s/.ssh" % username])

    # save key
    shell.run(["sudo", "sh", "-c", "cat %s/%s.pub >> /home/%s/.ssh/authorized_keys" % (config.ADMIN_HOME, username, username)])
    shell.run(["sudo", "chown", "-R", "%s:%s" % (username, username), "/home/%s/.ssh" % username])
    shell.run(["sudo", "chmod", "600", "/home/%s/.ssh/authorized_keys" % username])
    shell.run(["sudo", "chmod", "700", "/home/%s/.ssh" % username])

    # configure server
    shell.run(["sudo", "chsh", "-s", "/bin/bash", username])
    local_shell.run(["scp", "-i", config.KEY_STORAGE_PATH % username, config.VIMRC_PATH,
     "%s@%s:~/.vimrc" % (username, host)])
    local_shell.run(["scp", "-i", config.KEY_STORAGE_PATH % username, config.BASHRC_PATH,
     "%s@%s:~/.bashrc" % (username, host)])

@route('/', method='POST')
def new_user():
    key = request.POST.get('key')
    username = request.POST.get('username')
    key.save(config.KEY_STORAGE_PATH % username, overwrite=True)
    servers = open(config.SERVERS_PATH, 'r')
    for server in servers:
        send_key(username, server)
    servers.close()

@route('/servers', method='GET')
def servers():
    servers = open(config.SERVERS_PATH, 'r')
    res = []
    for server in servers:
        res.insert(0, server.strip())
    return '[%s]' % ', '.join(res)

if __name__ == '__main__':
    app = bottle.app()
    wsgi_server = gevent.wsgi.WSGIServer(('0.0.0.0', 8000), app)
    wsgi_server.serve_forever()
