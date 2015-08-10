"""
TODO:
- Store comic metadata (in relation to ID or title?) so that users can
    have several tabs open (and navigate between these)?
- Navigation while viewing comic (first/previous/random/next/last)
- Pad metadata panel and (derive value from sidebar width: viewport_extent(),
    layout_extent())
- Clean cache more often; currently only upon plugin reload.
    Call plugin_unloaded from panel-close, or remove all images not in
    xkcd_open[] ?
"""
import errno
import json
import os
import random
import sublime
import sublime_plugin
import sys
import urllib

global xkcd_open
xkcd_open = []

if sys.version_info < (3, 3):
    raise RuntimeError('Xkcd works with Sublime Text 3 only')


def plugin_loaded():
    """Called directly from sublime on plugin load."""
    try:
        os.makedirs(sublime.cache_path() + os.path.sep + 'Xkcd')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise IOError('Error encountered during file creation.')


def plugin_unloaded():
    """Called directly from sublime on plugin unload."""
    clean_cache()


def clean_cache():
    """Delete cache"""
    for fl in os.listdir(sublime.cache_path() + os.path.sep + 'Xkcd'):
        try:
            os.remove(sublime.cache_path() + os.path.sep + 'Xkcd' + os.path.sep + fl)
        except OSError as e:
            raise IOError('Could not remove previous files.')


def xJson(id=None):
    """Get JSON object from XKCD API."""
    if id is None:
        url = 'http://xkcd.com/info.0.json'
    else:
        url = 'http://xkcd.com/' + str(id) + '/info.0.json'

    try:
        request = urllib.request.Request(url, headers={"User-Agent":
                                                       "Sublime Xkcd"})
        opener = urllib.request.build_opener()
        f = opener.open(request)
        result = json.loads(f.read().decode("utf-8"))

        return result

    except urllib.error.HTTPError as e:
        err = '%s: HTTP error %s contacting API' % (__name__, str(e.code))
    except urllib.error.URLError as e:
        err = '%s: URL error %s contacting API' % (__name__, str(e.reason))


class EventDump(sublime_plugin.EventListener):

    """Event listener for automatic closing of meta-pane on image close."""

    global xkcd_open

    def on_load(self, view):
        """File Loaded."""
        # print (view.file_name(), "just got loaded")

    def on_new(self, view):
        """New file created."""
        # print ("new file")

    def on_modified(self, view):
        """File modified."""
        print (view.file_name(), "modified")
        #if view.file_name() == None:
        #print(view.command_history(0)[1])
            #if view.command_history(1)[0] == 'Up':
            #    print('Up, mofo!')
        #myKey = sublime.getkeypress()
        #print(myKey)

    def on_activated(self, view):
        """View activated."""
        # print (view.file_name(), "is now the active view")
        # xkcd_open.remove(self.num)
        if xkcd_open:
            try:
                xkcd_open.pop()
            except Exception as e:
                print(str(e))
            if view.file_name() != None:
                view.window().run_command(
                    "hide_panel", {"panel": "output.xkcd_meta"})


    def on_close(self, view):
        """View closed."""
        # print (view.file_name(), "is no more")
        clean_cache()


class XkcdGetComicCommand(sublime_plugin.WindowCommand):

    """Grab comic."""

    def run(self, id):
        """Main function, runs on activation."""
        # Grab comic via async background process
        sublime.set_timeout_async(self.getComic(id), 0)

    def getComic(self, id=None):
        """Background loop."""
        result = xJson(id)

        self.title = result['title']
        self.img = result['img']
        self.alt = result['alt']
        self.num = result['num']

        try:
            local_img = sublime.cache_path() + os.path.sep + 'Xkcd' + \
                os.path.sep + self.img.split('/')[-1]
            urllib.request.urlretrieve(self.img, local_img)

        except urllib.error.HTTPError as e:
            err = '%s: HTTP error %s contacting API' % (__name__, str(e.code))
        except urllib.error.URLError as e:
            err = '%s: URL error %s contacting API' % (__name__, str(e.reason))

        self.output = '[' + str(self.num) + '] ' + \
            self.title + '\n\n' + self.alt

        # sublime.error_message(err)

        panel = self.window.create_output_panel('xkcd_meta')
        panel.run_command('erase_view')
        self.window.run_command(
            "show_panel", {"panel": "output.xkcd_meta"})
        self.window.get_output_panel('xkcd_meta').run_command(
            'append', {'characters': self.output})
        panel.settings().set("word_wrap", True)
        # print(int(self.window.active_view().viewport_extent()[0]-self.window.active_view().layout_extent()[0]))

        self.window.open_file(local_img, sublime.TRANSIENT)

        global xkcd_open
        xkcd_open.append(self.num)

        # HANDLE NAVIGATION (first/previous/next/last) HERE...

        # self.view.run_command('push_tooltip', {'output': self.output})


class XkcdLatestCommand(sublime_plugin.WindowCommand):

    """Latest Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        self.window.run_command('xkcd_get_comic', {'id': None})


class XkcdRandomCommand(sublime_plugin.WindowCommand):

    """Random Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        latest = xJson()
        self.window.run_command(
            'xkcd_get_comic', {'id': random.randrange(latest['num'])})


class XkcdListCommand(sublime_plugin.WindowCommand):

    """List Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        url = 'http://xkcd.com/archive/'
        xml_str = str(urllib.request.urlopen(url).read()).split(
            '(Hover mouse over title to view publication date)<br /><br />',
            1)[-1].split(
            '</div>\\n<div id="bottom" class="box">', 1)[0].strip()
        clean_xml_str = xml_str.split('<br/>')

        self.menu_list = []
        # file = open("/Users/Eivind/Desktop/FILE.TXT", "w")
        # for line in clean_xml_str:
        #    file.write(line.strip('\\n')+'\n')
        # file.close()
        for line in clean_xml_str:
            if line is not None:
                line_id = line.split('"/', 1)[-1].split('/"', 1)[0]
                line_date = line.split('="', 2)[-1].split('">', 1)[0]
                line_title = line.split('">', 1)[-1].split('</', 1)[0]
                self.menu_list.append([line_title, line_id, line_date])

        sublime.set_timeout_async(self.window.show_quick_panel(
            self.menu_list, self.on_chosen), 0)

    def on_chosen(self, index):
        """Comic chosen from quick panel."""
        if index is not -1:
            self.window.run_command(
                'xkcd_get_comic', {'id': self.menu_list[index][1]})


class PushTooltipCommand(sublime_plugin.TextCommand):

    """Push tooltip."""

    def run(self, edit, output):
        """Main."""
        self.view.show_popup(str(output), on_navigate=print, location=-1)
