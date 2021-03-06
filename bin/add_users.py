#!/usr/bin/python

import os
import gnupg
import paramiko
import sys
import time

decrypted_pass = ''
chan = ''
userdict = {}
groupdict = {}

def populateUserDict():
    global userdict
    usertext = open('Users.txt','r').readlines()
    userlist = [ x.strip('\r\n').split('\t') for x in usertext ]
    for x in userlist:
         userdict[x[1]] = {
             'FullName': x[0],
             'Username': x[1],
             'Group': x[2],
             'UID': x[3],
             'SudoGroup': x[4],
         }

def populateGroupDict():
    global groupdict
    grouptext = open('Groups.txt','r').readlines()
    grouplist = [ x.strip('\r\n').split('\t') for x in grouptext ]
    for x in grouplist:
        groupdict[x[0]] = x[1]

def decryptPass():
    global decrypted_pass
    home = os.getenv('HOME')
    gpg = gnupg.GPG(gnupghome='%s/.gnupg/' % home)

    encrypted_pass = ''
    encrypted_pass = open('%s/.ssh/passtext.gpg' % home,'r').read()

    decrypted_pass = gpg.decrypt(encrypted_pass).data
    decrypted_pass = decrypted_pass.strip('\n')


def addGroups():
    global chan
    global groupdict
    for group, gid in groupdict.items():
        group_add = 'groupadd -g %s %s\n' % (gid,group,)
        chan.send(group_add)
        while not chan.recv_ready():
            time.sleep(2)
        print chan.recv(1024)

def addUsers():
    global chan
    global userdict
    usercmd = 'useradd -c "%s" -u %s -G %s -p "PASSWORDINAD" -m %s'
    usercmd += ' && chage -M 99999 %s'
    for user,uservals in userdict.items():
        if uservals['UID'] != 'UID':
            add_user = usercmd % (
                uservals['FullName'],
                uservals['UID'],
                uservals['Group'],
                uservals['Username'],
                uservals['Username'],
            )
            if uservals['SudoGroup']:
                add_user += ' && usermod -aG %s %s' % (
                    uservals['SudoGroup'],
                    uservals['Username'],
                )
            add_user += '\n'
            chan.send(add_user)
            while not chan.recv_ready():
                time.sleep(2)
            print chan.recv(1024)

def runRemoteShell():
    host = sys.argv[1]
    user = sys.argv[2]
    global chan
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host,username=user,password=decrypted_pass)
    chan = ssh.invoke_shell()
    while not chan.recv_ready():
        print "Connecting..."
        time.sleep(2)
    print(chan.recv(1024))
    chan.send('sudo su -\n')
    time.sleep(1)
    chan.send('%s\n' % decrypted_pass)
    print chan.recv(1024)
    while not chan.recv_ready():
        time.sleep(2)
    chan.send('pwd\n')
    print chan.recv(1024)
    print chan.recv(1024)
    addGroups()
    addUsers()

def main():
    try:
        populateUserDict()
        populateGroupDict()
        decryptPass()
        runRemoteShell()
        return 0
    except IndexError:
        exitmsg = '''
        Usage: %s ${HOSTNAME/IP} ${USERNAME}
        Please ensure both arguments are valid and present.
        '''
        exitmsg = exitmsg % (sys.argv[0],)
        print >> sys.stderr, exitmsg
        return 1

if __name__ == "__main__":
    sys.exit(main())
