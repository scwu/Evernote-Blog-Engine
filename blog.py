from __future__ import with_statement
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
        abort, render_template, flash
from contextlib import closing
from pagination import Pagination
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'evernote-sdk-python/lib/'))
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
from math import ceil
from flask import redirect 

PER_PAGE = 5

#configuration

DATABASE = '/tmp/blog.db'
DEBUG = True

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


@app.route('/', defaults = {'page':1})
@app.route('/<int:page>')
def show_entry(page):
    authToken = 'S=s101:U=a7c333:E=14195104dda:C=13a3d5f21da:P=1cd:A=en-devtoken:H=eed4b1d9c5f0c3a4240da55ee7a8de0f'
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
        if notebook.name == "Blog":
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
        content = row[2]
        entry = dict(created=readable, title=row[1], text=row[2])
        entries.append(entry)
    count = len(entries)
    final_values = page - 1
    smaller = page - 1
    larger = page + 1
    previous = True
    after = False
    if final_values == 0:
        previous = False
    if final_values + PER_PAGE < count:
        final_entries = entries[final_values:PER_PAGE]
    else:
        final_entries = entries[final_values:count]
        after = False
    if not entries and page != 1:
            abort(404)
    return render_template('show_entries.html', entries = final_entries, previous = previous, after = after, \
            smaller = smaller, larger = larger)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run()
