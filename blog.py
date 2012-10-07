from __future__ import with_statement
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
        abort, render_template, flash
from contextlib import closing
import sys
sys.path.append('evernote-sdk-python/lib/')
import hashlib
import binascii
import time
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors
import time
import oauth2 as oauth

#configuration

DATABASE = '/tmp/blog.db'
DEBUG = True
SECRET_KEY = 'development_key'
USERNAME = 'admin'
PASSWORD = 'default'

#create our application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('BLOG_SETTINGS', silent=True)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()
@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

@app.route('/')
def add_entry():
    authToken = 'INSERT HERE'
    if authToken == "wrong":
        print "Please fill in your developer token"
        print "To get a developer token, visit https://sandbox.evernote.com/api/DeveloperToken.action"
        exit(1)

    # https://www.evernote.com/api/DeveloperToken.action
    evernoteHost = "www.evernote.com"
    userStoreUri = "https://" + evernoteHost + "/edam/user"

    userStoreHttpClient = THttpClient.THttpClient(userStoreUri)
    userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
    userStore = UserStore.Client(userStoreProtocol)

    versionOK = userStore.checkVersion("Evernote EDAMTest (Python)",
                                   UserStoreConstants.EDAM_VERSION_MAJOR,
                                  UserStoreConstants.EDAM_VERSION_MINOR)
    if not versionOK:
        exit(1)

    noteStoreUrl = userStore.getNoteStoreUrl(authToken)
    noteStoreHttpClient = THttpClient.THttpClient(noteStoreUrl)
    noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
    noteStore = NoteStore.Client(noteStoreProtocol)
   
   #get access to default notebook
    notebooks = noteStore.listNotebooks(authToken)
    for notebook in notebooks:
        print notebook.name

    filter = NoteStore.NoteFilter()
    filter.notebookGuid = notebook.guid
    filter.order = Types.NoteSortOrder.UPDATED
    filter.ascending = False

    notes = noteStore.findNotes(authToken, filter, 0, 10000)
    for note in notes.notes:
        note = noteStore.getNote(authToken, note.guid, withContent=True, withResourcesData=True, withResourcesRecognition=False, withResourcesAlternateData=False)
        g.db.execute('insert or replace into entries (created, title, text) values (?, ?, ?)',
                [note.created, note.title, note.content.decode('utf-8')])
        g.db.commit()
    #Show all entries
    cur = g.db.execute('select created, title, text from entries order by created desc')
    entries = []
    for row in cur.fetchall():
        readable = time.ctime(row[0]/1000)
        entry = dict(created=readable, title=row[1], text=row[2])
        entries.append(entry)
    return render_template('show_entries.html', entries = entries)

if __name__ == '__main__':
    app.run()
